from __future__ import annotations

import io
import logging
import os
import time
from typing import Any, Dict, List, Tuple
import numpy as np
import pandas as pd
import polars as pl
import neurokit2 as nk
import xgboost as xgb

from src.extensions import db
from src.models.event_prediction import EventPrediction
from src.models.maximum_voluntary_contraction import MaximumVoluntaryContraction
from src.models.night_duration import NightDuration
from src.models.sensor_threshold import SensorThreshold
from src.models.sleep_stage_segment import SleepStageSegment
from src.utils.utils import (
    add_new_prediction,
    get_settings,
    aggregate_events,
    calculate_night_duration,
    extract_features_for_prediction,
    find_mvc,
    generate_night_images,
    get_continuous_features,
    get_new_event_metrics,
    parse_data_structure,
    read_loc_csv,
    rectify_signal,
    rms,
    sort_data_structure,
)
from src.ssd import analyze_hrv


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class PatientService:
    """All heavy-lifting lives here."""

    def __init__(self) -> None:
        self.__logger = logging.getLogger(__name__)
        self._settings = None

    @property
    def settings(self):
        if self._settings is None:
            self._settings = get_settings()
        return self._settings

    # ------------------------------------------------------------------ #
    #   1 · Patients (top-level)
    # ------------------------------------------------------------------ #

    def list_patients(self) -> List[int]:
        patients = sort_data_structure(
            parse_data_structure(self.settings.original_data_path)
        )
        return patients

    # ------------------------------------------------------------------ #
    #   2 · Weeks
    # ------------------------------------------------------------------ #

    def list_weeks(self, patient_id: int) -> List[str]:
        struct = self.patient_data(patient_id)
        return sorted(struct.keys())

    def week_summary(self, patient_id: int, week: str) -> Dict[str, Any]:
        # Quick example summary
        nights = self.list_nights(patient_id, week)
        return {"patientId": patient_id, "week": week, "nNights": len(nights)}

    # ------------------------------------------------------------------ #
    #   3 · Nights
    # ------------------------------------------------------------------ #

    def list_nights(self, patient_id: int, week: str) -> List[str]:
        struct = self.patient_data(patient_id)
        return sorted(struct.get(week, []))

    def night_meta(self, patient_id: int, week: str, night: str) -> Dict[str, Any]:
        dur = self.night_duration(patient_id, week, night).get("duration_s")
        flags = {
            "hasSSD": SleepStageSegment.query.filter_by(
                patient_id=patient_id, week=week, file=night
            ).first()
            is not None,
            "downsampled": os.path.isfile(
                f"{self.settings.downsampled_data_path}/p{patient_id}_wk{week}/{night[:-4]}200Hz.csv"
            ),
        }
        return {"duration_s": dur, **flags}

    def downsample_and_persist_recording(
        self, patient_id: int, week: str, night: str
    ) -> Dict[str, str]:
        original_data_path = get_settings().original_data_path
        downsampled_data_path = get_settings().downsampled_data_path

        emg_right_name = get_settings().emg_right_name  # 'MR'
        emg_left_name = get_settings().emg_left_name  # 'ML'
        ecg_name = get_settings().ecg_name  # 'ECG'

        original_sampling_rate = get_settings().original_sampling_rate  # 2000
        minimum_sampling_rate = get_settings().minimum_sampling_rate  # 200

        if os.path.isfile(
            f"{downsampled_data_path}/p{patient_id}_wk{week}/{night[:-4]}200Hz.csv"
        ):
            return "Data already downsampled"

        else:
            self.__logger.info("Open datasets")
            data = pl.read_csv(
                f"{original_data_path}/p{patient_id}_wk{week}/{night}",
                columns=[emg_right_name, emg_left_name, ecg_name],
            )
            loc = read_loc_csv(patient_id, week, night)

            # Check that there are no null values in the recording
            df_missing = data.filter(pl.any_horizontal(pl.all().is_null()))

            self.__logger.info(df_missing)

            if len(df_missing) > 0:
                self.__logger.info("fill")
                # Fill null values
                data = data.with_columns(pl.all().fill_null(strategy="backward"))

            mr = data.get_column(emg_right_name)
            ml = data.get_column(emg_left_name)
            ecg = data.get_column(ecg_name)

            calculate_night_duration(
                patient_id, week, night, len(mr), sampling_rate=original_sampling_rate
            )

            self.__logger.info("Extract MaximumVoluntaryContraction")

            last_index = int(loc[2, 1])
            self.__logger.info(last_index)
            mr_short = mr[: last_index + 1]
            ml_short = ml[: last_index + 1]

            self.__logger.info("rectify")
            self.__logger.info(mr_short)
            self.__logger.info(type(mr_short))
            mr_rect = rectify_signal(mr_short)
            ml_rect = rectify_signal(ml_short)

            mr_rect = pd.DataFrame(mr_rect)
            ml_rect = pd.DataFrame(ml_rect)

            self.__logger.info("calculate rms")
            mr_rms = rms(mr_rect, sampling=original_sampling_rate)
            ml_rms = rms(ml_rect, sampling=original_sampling_rate)

            self.__logger.info("find mvc")
            mr_mvc = find_mvc(mr_rms, loc)
            ml_mvc = find_mvc(ml_rms, loc)

            self.__logger.info("save MaximumVoluntaryContraction to db")
            mr_mvc_db = MaximumVoluntaryContraction(
                patient_id=patient_id,
                week=week,
                file=night,
                sensor=emg_right_name,
                mvc=mr_mvc.item(),
            )
            ml_mvc_db = MaximumVoluntaryContraction(
                patient_id=patient_id,
                week=week,
                file=night,
                sensor=emg_left_name,
                mvc=ml_mvc.item(),
            )
            db.session.add(mr_mvc_db)
            db.session.add(ml_mvc_db)

            db.session.commit()

            mr_ds = nk.signal_resample(
                mr,
                sampling_rate=original_sampling_rate,
                desired_sampling_rate=minimum_sampling_rate,
            )
            ml_ds = nk.signal_resample(
                ml,
                sampling_rate=original_sampling_rate,
                desired_sampling_rate=minimum_sampling_rate,
            )
            ecg_ds = nk.signal_resample(
                ecg,
                sampling_rate=original_sampling_rate,
                desired_sampling_rate=minimum_sampling_rate,
            )

            new_df = pd.DataFrame(
                {emg_right_name: mr_ds, emg_left_name: ml_ds, ecg_name: ecg_ds}
            )

            if not os.path.exists(f"{downsampled_data_path}/p{patient_id}_wk{week}"):
                os.makedirs(f"{downsampled_data_path}/p{patient_id}_wk{week}")

            new_df.to_csv(
                f"{downsampled_data_path}/p{patient_id}_wk{week}/{night[:-4]}200Hz.csv"
            )

            return "Data downsampled and saved correctly."

    # 3.1 metrics & raw -------------------------------------------------

    def get_night_duration(
        self, patient_id: int, week: str, night: str
    ) -> Dict[str, int] | str:
        night_duration = NightDuration.query.filter_by(
            patient_id=patient_id, week=week, file=night
        ).first()
        self.__logger.info(night_duration.seconds)

        if night_duration is None:
            return "No night duration for this night."

        else:
            return {"duration_s": night_duration.seconds}

    def get_night_maximum_voluntary_contraction(
        self, patient_id: int, week: str, night: str
    ) -> Dict[str, int]:
        emg_right_name = get_settings().emg_right_name  # 'MR'
        emg_left_name = get_settings().emg_left_name  # 'ML'

        mvc_mr = MaximumVoluntaryContraction.query.filter_by(
            patient_id=patient_id, week=week, file=night, sensor=emg_right_name
        ).first()
        mvc_ml = MaximumVoluntaryContraction.query.filter_by(
            patient_id=patient_id, week=week, file=night, sensor=emg_left_name
        ).first()

        if mvc_mr is None or mvc_ml is None:
            return "No MaximumVoluntaryContraction for this night.", 404

        else:
            return {
                "mvc_mr": mvc_mr.mvc,
                "mvc_ml": mvc_ml.mvc,
            }

    def fetch_sleep_stage(self, patient_id: int, week: str, night: str):
        rows = SleepStageSegment.query.filter_by(
            patient_id=patient_id, week=week, file=night
        ).all()
        return [
            {
                "HRV_LFHF": r.HRV_LFHF,
                "HRV_SDNN": r.HRV_SDNN,
                "x": r.x,
                "y": r.y,
                "stage": r.stage,
            }
            for r in rows
        ]

    # --- compute / (re)compute ---------------------------------------
    def generate_sleep_stage_segments(
        self, patient_id: int, week: str, night: str, sampling_rate: int
    ) -> bool:
        """Return True if we *started* a new computation, False if data existed."""

        # If rows already exist → do nothing, stay idempotent
        if SleepStageSegment.query.filter_by(
            patient_id=patient_id, week=week, file=night
        ).first():
            return False

        # Either run synchronously …
        analyze_hrv(
            patient_id, week, night, sampling_rate
        )  # TODO: Investigate utils script

        # … or kick off a Celery/RQ task here and
        # return immediately (better for long nights).
        return True

    def get_emg_window(
        self, patient_id: int, week: str, night: str, five_minute_window_index: float
    ) -> Dict[str, Any]:
        downsampled_data_path = get_settings().downsampled_data_path
        minimum_sampling_rate = get_settings().minimum_sampling_rate  # 200
        emg_right_name = get_settings().emg_right_name  # 'MR'
        emg_left_name = get_settings().emg_left_name  # 'ML'

        start = time.time()

        total_seconds = (
            NightDuration.query.filter_by(patient_id=patient_id, week=week, file=night)
            .first()
            .seconds
        )
        self.__logger.info(total_seconds)
        data_length = int(total_seconds * minimum_sampling_rate)

        start_id = int(minimum_sampling_rate * 60 * 5 * five_minute_window_index)
        end_id = start_id + minimum_sampling_rate * 60 * 5

        self.__logger.info("open file")
        data = pl.read_csv(
            f"{downsampled_data_path}/p{patient_id}_wk{week}/{night[:-4]}200Hz.csv",
            columns=[emg_right_name, emg_left_name],
            skip_rows_after_header=start_id,
            n_rows=end_id - start_id,
        )
        features = pl.read_csv(
            f"{downsampled_data_path}/p{patient_id}_wk{week}/{night[:-4]}200Hz_features.csv"
        )

        mr = pd.Series(data[emg_right_name].to_list())
        ml = pd.Series(data[emg_left_name].to_list())

        # Rectify
        self.__logger.info("rectify the signal")
        mr_rect = rectify_signal(mr)
        ml_rect = rectify_signal(ml)

        self.__logger.info("calculate rms")
        mr_rms = rms(mr_rect, sampling=minimum_sampling_rate)
        ml_rms = rms(ml_rect, sampling=minimum_sampling_rate)

        self.__logger.info(mr_rms)

        num_samples = len(mr_rms)
        if end_id >= data_length:
            self.__logger.info("last window")
        start_time = (
            start_id / minimum_sampling_rate
        )  # Convert start index to seconds (since original is at 2000 Hz)

        emg_time = np.linspace(
            start_time,
            start_time + num_samples / minimum_sampling_rate,
            num_samples,
            endpoint=False,
        )

        continuous_features = get_continuous_features(
            features, five_minute_window_index, data_length=len(mr_rms)
        )
        self.__logger.info("len features: ")
        self.__logger.info(len(continuous_features["std_mr"]))
        emg_window = {
            emg_right_name: mr_rms.tolist(),
            emg_left_name: ml_rms.tolist(),
            "EMG_t": emg_time.tolist(),
        }
        end = time.time()

        self.__logger.info(f"{end-start} seconds taken.")

        return emg_window | continuous_features

    # 3.2 thresholds ----------------------------------------------------

    def get_thresholds(self, patient_id: int, week: str, night: str) -> Dict[str, int]:
        emg_right_sensor, emg_left_sensor = (
            self.settings.emg_right_name,
            self.settings.emg_left_name,
        )
        threshold_records = SensorThreshold.query.filter_by(
            patient_id=patient_id, week=week, file=night
        ).all()

        def default_thresholds() -> Dict[str, int]:
            return {emg_right_sensor: 10, emg_left_sensor: 10}

        if not threshold_records:
            return default_thresholds()

        result = {record.sensor: record.threshold_value for record in threshold_records}
        for sensor in (emg_right_sensor, emg_left_sensor):
            result.setdefault(sensor, 10)
        return result

    def post_threshold(
        self,
        patient_id: int,
        week: str,
        night: str,
        sensor: str,
        payload: Dict[str, Any],
    ) -> Dict[str, str]:
        threshold_value = payload.get("threshold")
        existing_record = SensorThreshold.query.filter_by(
            patient_id=patient_id, week=week, file=night, sensor=sensor
        ).first()

        # TODO: Refactor this into PUT and POST methods
        if existing_record:
            existing_record.threshold_value = threshold_value
        else:
            new_record = SensorThreshold(
                patient_id=patient_id,
                week=week,
                file=night,
                sensor=sensor,
                threshold_value=threshold_value,
            )
            db.session.add(new_record)
        db.session.commit()
        return {"message": "Threshold updated."}

    # 3.3 images --------------------------------------------------------

    def get_night_images(
        self, patient_id: int, week: str, night: str, refresh: bool = False
    ):
        base = (
            f"{self.settings.downsampled_data_path}/"
            f"p{patient_id}_wk{week}/{night[:-4]}200Hz.csv_images"
        )

        if refresh or not os.path.isdir(base):
            try:
                mr, ml = self.__load_emg_signals(patient_id, week, night)
            except FileNotFoundError:
                # Optionally trigger downsample_and_persist_recording here, or raise
                self.__logger.error("Downsampled EMG data missing for image generation")
                raise

            # Fetch events/predictions for marking on plots
            predictions = EventPrediction.query.filter_by(
                patient_id=patient_id, week=week, file=night
            ).all()

            generate_night_images(
                patient_id, week, night, mr, ml, predictions
            )  # TODO: Seperate GET and POST logic

        files = sorted(f for f in os.listdir(base) if f.endswith(".png"))
        return [
            {
                "label": (
                    "Whole Night Signal"
                    if "whole_night_signal" in file_name
                    else f"Sleep Cycle {file_name.split('_')[2][:-4]}"
                ),
                "src": f"/patients/{patient_id}/weeks/{week}/nights/{night}/images/{file_name}",
                "filename": file_name,
            }
            for file_name in files
        ]

    def get_night_image(
        self, patient_id: int, week: str, night: str, filename: str
    ) -> Tuple[str, str]:
        directory = (
            f"{self.settings.downsampled_data_path}/"
            f"p{patient_id}_wk{week}/{night[:-4]}200Hz.csv_images"
        )
        return directory, filename

    # ------------------------------------------------------------------ #
    #   4 · Events
    # ------------------------------------------------------------------ #

    def get_events(
        self, patient_id: int, week: str, night: str
    ) -> List[Dict[str, Any]]:
        events = EventPrediction.query.filter_by(
            patient_id=patient_id, week=week, file=night
        ).all()

        downsampled_data_path = get_settings().downsampled_data_path
        model_path = get_settings().model_path

        minimum_sampling_rate = get_settings().minimum_sampling_rate  # 200

        model_file_name = get_settings().model_file_name

        if not events:

            if os.path.isfile(
                f"{downsampled_data_path}/p{patient_id}_wk{week}/{night[:-4]}200Hz_features.csv"
            ):
                features = pd.read_csv(
                    f"{downsampled_data_path}/p{patient_id}_wk{week}/{night[:-4]}200Hz_features.csv"
                )

                times = features.iloc[:, 1:3]
                features = features.iloc[:, 3:43]

            else:
                sensor_data = pd.read_csv(
                    f"{downsampled_data_path}/p{patient_id}_wk{week}/{night[:-4]}200Hz.csv"
                )
                features = extract_features_for_prediction(
                    sensor_data, sampling_rate=minimum_sampling_rate
                )
                self.__logger.info("Writing features to csv")

                features.to_csv(
                    f"{downsampled_data_path}/p{patient_id}_wk{week}/{night[:-4]}200Hz_features.csv"
                )

                times = features.iloc[:, 0:2]
                features = features.iloc[:, 2:42]

            # Load model
            loaded_model = xgb.XGBClassifier()
            loaded_model.load_model(f"{model_path}/{model_file_name}")

            y_pred = loaded_model.predict(features)

            y_pred_proba = loaded_model.predict_proba(
                features
            )  # Probabilities for each class

            self.__logger.info(f"Predicted class labels for new data: {y_pred}")

            self.__logger.info(f"Predicted probabilities for new data: {y_pred_proba}")

            unique, counts = np.unique(y_pred, return_counts=True)

            self.__logger.info(f"EventPrediction: {dict(zip(unique, counts))}")

            result = pd.concat([times, features], axis=1)
            result["y"] = y_pred
            result["y_prob"] = [max(p) for p in y_pred_proba]

            # self.__logger.info(result)

            events = result[result["y"] == 1]
            events["confirmed"] = True

            self.__logger.info(events)

            events_with_features = aggregate_events(events)

            for key in events_with_features:
                event_db = EventPrediction(
                    patient_id=patient_id,
                    week=week,
                    file=night,
                    name=key,
                    start_s=events_with_features[key]["start_s"],
                    end_s=events_with_features[key]["end_s"],
                    std_mr=events_with_features[key]["std_mr"].item(),
                    std_ml=events_with_features[key]["std_ml"].item(),
                    var_mr=events_with_features[key]["var_mr"].item(),
                    var_ml=events_with_features[key]["var_ml"].item(),
                    rms_mr=events_with_features[key]["rms_mr"].item(),
                    rms_ml=events_with_features[key]["rms_ml"].item(),
                    mav_mr=events_with_features[key]["mav_mr"].item(),
                    mav_ml=events_with_features[key]["mav_ml"].item(),
                    log_det_mr=events_with_features[key]["log_det_mr"].item(),
                    log_det_ml=events_with_features[key]["log_det_ml"].item(),
                    wl_mr=events_with_features[key]["wl_mr"].item(),
                    wl_ml=events_with_features[key]["wl_ml"].item(),
                    aac_mr=events_with_features[key]["aac_mr"].item(),
                    aac_ml=events_with_features[key]["aac_ml"].item(),
                    dasdv_mr=events_with_features[key]["dasdv_mr"].item(),
                    dasdv_ml=events_with_features[key]["dasdv_ml"].item(),
                    wamp_mr=events_with_features[key]["wamp_mr"].item(),
                    wamp_ml=events_with_features[key]["wamp_ml"].item(),
                    fr_mr=events_with_features[key]["fr_mr"].item(),
                    fr_ml=events_with_features[key]["fr_ml"].item(),
                    mnp_mr=events_with_features[key]["mnp_mr"].item(),
                    mnp_ml=events_with_features[key]["mnp_ml"].item(),
                    tot_mr=events_with_features[key]["tot_mr"].item(),
                    tot_ml=events_with_features[key]["tot_ml"].item(),
                    mnf_mr=events_with_features[key]["mnf_mr"].item(),
                    mnf_ml=events_with_features[key]["mnf_ml"].item(),
                    mdf_mr=events_with_features[key]["mdf_mr"].item(),
                    mdf_ml=events_with_features[key]["mdf_ml"].item(),
                    pkf_mr=events_with_features[key]["pkf_mr"].item(),
                    pkf_ml=events_with_features[key]["pkf_ml"].item(),
                    HRV_mean=events_with_features[key]["HRV_mean"].item(),
                    HRV_median=events_with_features[key]["HRV_median"].item(),
                    HRV_sdnn=events_with_features[key]["HRV_sdnn"].item(),
                    HRV_min=events_with_features[key]["HRV_min"].item(),
                    HRV_max=events_with_features[key]["HRV_max"].item(),
                    HRV_vhf=events_with_features[key]["HRV_vhf"].item(),
                    HRV_lf=events_with_features[key]["HRV_lf"].item(),
                    HRV_hf=events_with_features[key]["HRV_hf"].item(),
                    HRV_lf_hf=events_with_features[key]["HRV_lf_hf"].item(),
                    RRI=events_with_features[key]["RRI"].item(),
                    y_prob=events_with_features[key]["y_prob"].item(),
                    confirmed=True,
                    sensor="both",
                    event_type="",
                    status="model",
                    justification="",
                )

                db.session.add(event_db)

            db.session.commit()

            return events_with_features
        else:
            result = {}
            for event in events:
                result[event.name] = {
                    "start_s": event.start_s,
                    "end_s": event.end_s,
                    "std_mr": event.std_mr,
                    "std_ml": event.std_ml,
                    "var_mr": event.var_mr,
                    "var_ml": event.var_ml,
                    "rms_mr": event.rms_mr,
                    "rms_ml": event.rms_ml,
                    "mav_mr": event.mav_mr,
                    "mav_ml": event.mav_ml,
                    "log_det_mr": event.log_det_mr,
                    "log_det_ml": event.log_det_ml,
                    "wl_mr": event.wl_mr,
                    "wl_ml": event.wl_ml,
                    "aac_mr": event.aac_mr,
                    "aac_ml": event.aac_ml,
                    "dasdv_mr": event.dasdv_mr,
                    "dasdv_ml": event.dasdv_ml,
                    "wamp_mr": event.wamp_mr,
                    "wamp_ml": event.wamp_ml,
                    "fr_mr": event.fr_mr,
                    "fr_ml": event.fr_ml,
                    "mnp_mr": event.mnp_mr,
                    "mnp_ml": event.mnp_ml,
                    "tot_mr": event.tot_mr,
                    "tot_ml": event.tot_ml,
                    "mnf_mr": event.mnf_mr,
                    "mnf_ml": event.mnf_ml,
                    "mdf_mr": event.mdf_mr,
                    "mdf_ml": event.mdf_ml,
                    "pkf_mr": event.pkf_mr,
                    "pkf_ml": event.pkf_ml,
                    "HRV_mean": event.HRV_mean,
                    "HRV_median": event.HRV_median,
                    "HRV_sdnn": event.HRV_sdnn,
                    "HRV_min": event.HRV_min,
                    "HRV_max": event.HRV_max,
                    "HRV_vhf": event.HRV_vhf,
                    "HRV_lf": event.HRV_lf,
                    "HRV_hf": event.HRV_hf,
                    "HRV_lf_hf": event.HRV_lf_hf,
                    "RRI": event.RRI,
                    "y_prob": event.y_prob,
                    "confirmed": event.confirmed,
                    "sensor": event.sensor,
                    "event_type": event.event_type,
                    "status": event.status,
                    "justification": event.justification,
                }

            return result

    def create_event(
        self, patient_id: int, week: str, night: str, event_details: Dict[str, Any]
    ):
        events = EventPrediction.query.filter_by(
            patient_id=patient_id, week=week, file=night
        ).all()
        emg_right_name = get_settings().emg_right_name  # 'MR'
        emg_left_name = get_settings().emg_left_name  # 'ML'

        print(event_details)

        start_s = float(event_details["start_s"])
        end_s = float(event_details["end_s"])
        event_type = event_details["event_type"]

        sensor = event_details["sensor"]

        if set(sensor) == set([emg_left_name]):
            sensor = emg_left_name
        if set(sensor) == set([emg_right_name]):
            sensor = emg_right_name
        if set(sensor) == set([emg_left_name, emg_right_name]):
            sensor = "both"

        justification = event_details["justification"]
        print(start_s, end_s, justification)

        # Calculate metrics
        metrics = get_new_event_metrics(patient_id, week, night, start_s, end_s)

        print(metrics)

        # Get new event name and rename others
        if not events:
            print("Add prediction with name e1")
            name = "e1"

            add_new_prediction(
                patient_id,
                week,
                night,
                start_s,
                end_s,
                event_type,
                sensor,
                justification,
                name,
                metrics,
            )

        else:
            print("logic to find new event position")
            events_after = (
                EventPrediction.query.filter(
                    EventPrediction.patient_id == patient_id,
                    EventPrediction.week == week,
                    EventPrediction.file == night,
                    EventPrediction.start_s >= start_s,
                )
                .order_by(EventPrediction.start_s)
                .all()
            )

            print(f"Event after: {events_after}")
            if events_after:
                name = events_after[0].name
                position = int(name[1:])

                for event in events_after:
                    position += 1
                    event.name = f"e{position}"
                db.session.commit()
                add_new_prediction(
                    patient_id,
                    week,
                    night,
                    start_s,
                    end_s,
                    event_type,
                    sensor,
                    justification,
                    name,
                    metrics,
                )

            else:
                last_event = (
                    EventPrediction.query.filter(
                        EventPrediction.patient_id == patient_id,
                        EventPrediction.week == week,
                        EventPrediction.file == night,
                        EventPrediction.start_s < start_s,
                    )
                    .order_by(EventPrediction.start_s.desc())
                    .first()
                )

                print("Last event: ", last_event.name)

                last_position = int(last_event.name[1:])
                name = f"e{last_position + 1}"

                add_new_prediction(
                    patient_id,
                    week,
                    night,
                    start_s,
                    end_s,
                    event_type,
                    sensor,
                    justification,
                    name,
                    metrics,
                )

        return "Post event added by expert."

    def patch_event(
        self,
        patient_id: int,
        week: str,
        night: str,
        event_name: str,
        patch_data: Dict[str, Any],
    ):
        event = EventPrediction.query.filter_by(
            patient_id=patient_id, week=week, file=night, name=event_name
        ).first()

        if not event:
            return {"error": "Event not found"}

        allowed_fields = [
            "start_s",
            "end_s",
            "confirmed",
            "justification",
            "sensor",
            "event_type",
            "status",
        ]

        for field in allowed_fields:
            if field in patch_data:
                setattr(event, field, patch_data[field])

        if (
            "start_s" in patch_data or "end_s" in patch_data
        ) and event.status != "modified":
            event.status = "modified"

        db.session.commit()
        return {"message": "Event updated successfully."}

    # ---- download all confirmed events --------------------------------

    def download_confirmed_events(self) -> Tuple[str, str]:
        conf = EventPrediction.query.filter_by(confirmed=True).all()
        df = pd.DataFrame([self.__to_event_dict(r) for r in conf])
        df.sort_values(["patient_id", "week", "file", "name"], inplace=True)

        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="xlsxwriter") as xl:
            df.to_excel(xl, index=False, sheet_name="Confirmed Events")
        out.seek(0)

        # Save to tmp dir so send_from_directory can stream it.
        tmp = "/tmp/confirmed_events.xlsx"
        with open(tmp, "wb") as fh:
            fh.write(out.read())
        return "/tmp", "confirmed_events.xlsx"

    # ------------------------------------------------------------------ #
    #   5 · Model service
    # ------------------------------------------------------------------ #

    def feature_importance(self) -> List[Tuple[str, float]]:
        model = self.__load_model()
        imp = model.feature_importances_.tolist()
        names = model.get_booster().feature_names
        return sorted(zip(names, imp), key=lambda x: x[1], reverse=True)

    def model_summary(self) -> Dict[str, Any]:
        return self.__load_model().get_params()

    # ------------------------------------------------------------------ #
    #   Helpers
    # ------------------------------------------------------------------ #

    def __load_model(self) -> xgb.XGBClassifier:
        model = xgb.XGBClassifier()
        model.load_model(f"{self.settings.model_path}/{self.settings.model_file_name}")
        return model

    def __to_event_dict(self, r: EventPrediction) -> Dict[str, Any]:
        # Serialize SQL row → dict (fields trimmed for brevity)
        return {
            "name": r.name,
            "start_s": r.start_s,
            "end_s": r.end_s,
            "confirmed": r.confirmed,
            "sensor": r.sensor,
            "event_type": r.event_type,
            "status": r.status,
            "justification": r.justification,
            "patient_id": r.patient_id,
            "week": r.week,
            "file": r.file,
            "y_prob": r.y_prob,
        }

    def __load_emg_signals(self, patient_id, week, night):
        downsampled_data_path = self.settings.downsampled_data_path
        emg_right_name = self.settings.emg_right_name
        emg_left_name = self.settings.emg_left_name

        path = f"{downsampled_data_path}/p{patient_id}_wk{week}/{night[:-4]}200Hz.csv"
        if not os.path.isfile(path):
            raise FileNotFoundError("Downsampled data missing.")

        import pandas as pd

        df = pd.read_csv(path)
        mr = df[emg_right_name].values
        ml = df[emg_left_name].values

        return mr, ml
