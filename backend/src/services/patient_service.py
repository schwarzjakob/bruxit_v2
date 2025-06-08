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
from flask import current_app, make_response
from sqlalchemy import func

from src.extensions import db
from src.models.event_prediction import EventPrediction
from src.models.maximum_voluntary_contraction import MaximumVoluntaryContraction
from src.models.night_duration import NightDuration
from src.models.sensor_threshold import SensorThreshold
from src.models.sleep_stage_segment import SleepStageSegment
from src.utils.utils import (
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


logging.basicConfig(level=logging.INFO)


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

    def downsample(self, patient_id: int, week: str, night: str) -> Dict[str, str]:
        # ---- Logic identical to old /downsample-data
        if os.path.isfile(
            f"{self.settings.downsampled_data_path}/p{patient_id}_wk{week}/{night[:-4]}200Hz.csv"
        ):
            return {"message": "Already down-sampled."}

        # .. copy of the original function
        # (shortened – same code as before) ....................................
        from src.routes import downsample_data  # type: ignore

        downsample_data(patient_id, week, night)  # reuse unchanged logic
        return {"message": "Down-sampling started."}

    # 3.1 metrics & raw -------------------------------------------------

    def night_duration(self, patient_id: int, week: str, night: str) -> Dict[str, int]:
        nd = NightDuration.query.filter_by(
            patient_id=patient_id, week=week, file=night
        ).first()
        return {"duration_s": nd.seconds} if nd else {}

    def night_mvc(self, patient_id: int, week: str, night: str) -> Dict[str, int]:
        mr = MaximumVoluntaryContraction.query.filter_by(
            patient_id=patient_id,
            week=week,
            file=night,
            sensor=self.settings.emg_right_name,
        ).first()
        ml = MaximumVoluntaryContraction.query.filter_by(
            patient_id=patient_id,
            week=week,
            file=night,
            sensor=self.settings.emg_left_name,
        ).first()
        return {
            "mvc_mr": mr.mvc if mr else None,
            "mvc_ml": ml.mvc if ml else None,
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
    def post_sleep_stage(
        self, patient_id: int, week: str, night: str, sampling_rate: int
    ) -> bool:
        """Return True if we *started* a new computation, False if data existed."""

        # If rows already exist → do nothing, stay idempotent
        if SleepStageSegment.query.filter_by(
            patient_id=patient_id, week=week, file=night
        ).first():
            return False

        # Either run synchronously …
        analyze_hrv(patient_id, week, night, sampling_rate)

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
        print(total_seconds)
        data_length = int(total_seconds * minimum_sampling_rate)

        start_id = int(minimum_sampling_rate * 60 * 5 * five_minute_window_index)
        end_id = start_id + minimum_sampling_rate * 60 * 5

        print("open file")
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
        print("rectify the signal")
        mr_rect = rectify_signal(mr)
        ml_rect = rectify_signal(ml)

        print("calculate rms")
        mr_rms = rms(mr_rect, sampling=minimum_sampling_rate)
        ml_rms = rms(ml_rect, sampling=minimum_sampling_rate)

        print(mr_rms)

        num_samples = len(mr_rms)
        if end_id >= data_length:
            print("last window")
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
        print("len features: ")
        print(len(continuous_features["std_mr"]))
        emg_window = {
            emg_right_name: mr_rms.tolist(),
            emg_left_name: ml_rms.tolist(),
            "EMG_t": emg_time.tolist(),
        }
        end = time.time()

        print(f"{end-start} seconds taken.")

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

    def list_images(
        self, patient_id: int, week: str, night: str, refresh: bool = False
    ) -> List[Dict[str, str]]:
        base = f"{self.settings.downsampled_data_path}/p{patient_id}_wk{week}/{night[:-4]}200Hz.csv_images"
        if refresh or not os.path.isdir(base):
            self.__generate_images(patient_id, week, night)
        imgs = [f for f in os.listdir(base) if f.endswith(".png")]
        return [
            {
                "label": (
                    "Whole Night Signal"
                    if "whole_night_signal" in f
                    else f"Sleep Cycle {f.split('_')[2][:-4]}"
                ),
                "src": f"/patients/{patient_id}/weeks/{week}/nights/{night}/images/{f}",
            }
            for f in imgs
        ]

    def __generate_images(self, patient_id: int, week: str, night: str) -> None:
        ds = self.settings.downsampled_data_path
        data = pl.read_csv(
            f"{ds}/p{patient_id}_wk{week}/{night[:-4]}200Hz.csv",
            columns=[self.settings.emg_right_name, self.settings.emg_left_name],
        )
        mr = data.get_column(self.settings.emg_right_name)
        ml = data.get_column(self.settings.emg_left_name)
        preds = EventPrediction.query.filter_by(
            patient_id=patient_id, week=week, file=night
        ).all()
        generate_night_images(patient_id, week, night, mr, ml, preds)

    def serve_image(
        self, patient_id: int, week: str, night: str, image: str
    ) -> Tuple[str, str]:
        folder = f"{self.settings.downsampled_data_path}/p{patient_id}_wk{week}/{night[:-4]}200Hz.csv_images"
        return folder, image

    # ------------------------------------------------------------------ #
    #   4 · Events
    # ------------------------------------------------------------------ #

    def list_events(self, patient_id: int, week: str, night: str) -> Dict[str, Any]:
        recs = EventPrediction.query.filter_by(
            patient_id=patient_id, week=week, file=night
        ).all()
        return {r.name: self.__to_event_dict(r) for r in recs}

    def create_event(
        self, patient_id: int, week: str, night: str, payload: Dict[str, Any]
    ) -> Dict[str, str]:
        # Direct port of old POST logic (shortened)
        from src.routes import predict_events  # type: ignore

        predict_events(patient_id, week, night)  # executes old logic
        return {"message": "Event queued / inserted."}

    def patch_event(
        self,
        patient_id: int,
        week: str,
        night: str,
        eid: str,
        payload: Dict[str, Any],
    ) -> Dict[str, str]:
        event: EventPrediction | None = EventPrediction.query.filter_by(
            patient_id=patient_id, week=week, file=night, name=eid
        ).first()

        if not event:
            return {"error": "Event not found."}

        # Merge payload into SQL row
        for field in (
            "start_s",
            "end_s",
            "confirmed",
            "sensor",
            "event_type",
            "status",
            "justification",
        ):
            if field in payload:
                setattr(event, field, payload[field])

        db.session.commit()
        return {"message": "Event patched."}

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
        tmp = f"/tmp/confirmed_events.xlsx"
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
