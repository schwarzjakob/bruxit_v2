from __future__ import annotations

import io
import logging
import os
from typing import Any, Dict, List, Tuple

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

    def list_weeks(self, pid: int) -> List[str]:
        struct = self.patient_data(pid)
        return sorted(struct.keys())

    def week_summary(self, pid: int, week: str) -> Dict[str, Any]:
        # Quick example summary
        nights = self.list_nights(pid, week)
        return {"patientId": pid, "week": week, "nNights": len(nights)}

    # ------------------------------------------------------------------ #
    #   3 · Nights
    # ------------------------------------------------------------------ #

    def list_nights(self, pid: int, week: str) -> List[str]:
        struct = self.patient_data(pid)
        return sorted(struct.get(week, []))

    def night_meta(self, pid: int, week: str, night: str) -> Dict[str, Any]:
        dur = self.night_duration(pid, week, night).get("duration_s")
        flags = {
            "hasSSD": SleepStageSegment.query.filter_by(
                patient_id=pid, week=week, file=night
            ).first()
            is not None,
            "downsampled": os.path.isfile(
                f"{self.settings.downsampled_data_path}/p{pid}_wk{week}/{night[:-4]}200Hz.csv"
            ),
        }
        return {"duration_s": dur, **flags}

    def downsample(self, pid: int, week: str, night: str) -> Dict[str, str]:
        # ---- Logic identical to old /downsample-data
        if os.path.isfile(
            f"{self.settings.downsampled_data_path}/p{pid}_wk{week}/{night[:-4]}200Hz.csv"
        ):
            return {"message": "Already down-sampled."}

        # .. copy of the original function
        # (shortened – same code as before) ....................................
        from src.routes import downsample_data  # type: ignore

        downsample_data(pid, week, night)  # reuse unchanged logic
        return {"message": "Down-sampling started."}

    # 3.1 metrics & raw -------------------------------------------------

    def night_duration(self, pid: int, week: str, night: str) -> Dict[str, int]:
        nd = NightDuration.query.filter_by(
            patient_id=pid, week=week, file=night
        ).first()
        return {"duration_s": nd.seconds} if nd else {}

    def night_mvc(self, pid: int, week: str, night: str) -> Dict[str, int]:
        mr = MaximumVoluntaryContraction.query.filter_by(
            patient_id=pid, week=week, file=night, sensor=self.settings.emg_right_name
        ).first()
        ml = MaximumVoluntaryContraction.query.filter_by(
            patient_id=pid, week=week, file=night, sensor=self.settings.emg_left_name
        ).first()
        return {
            "mvc_mr": mr.mvc if mr else None,
            "mvc_ml": ml.mvc if ml else None,
        }

    def fetch_sleep_stage(self, pid: int, week: str, night: str):
        rows = SleepStageSegment.query.filter_by(
            patient_id=pid, week=week, file=night
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
        self, pid: int, week: str, night: str, sampling_rate: int
    ) -> bool:
        """Return True if we *started* a new computation, False if data existed."""

        # If rows already exist → do nothing, stay idempotent
        if SleepStageSegment.query.filter_by(
            patient_id=pid, week=week, file=night
        ).first():
            return False

        # Either run synchronously …
        analyze_hrv(pid, week, night, sampling_rate)

        # … or kick off a Celery/RQ task here and
        # return immediately (better for long nights).
        return True

    def emg_window(self, pid: int, week: str, night: str, idx: float) -> Dict[str, Any]:
        # Straight copy of old get_emg
        return from_routes_get_emg(pid, week, night, idx)  # type: ignore

    # 3.2 thresholds ----------------------------------------------------

    def get_thresholds(self, pid: int, week: str, night: str) -> Dict[str, int]:
        emg_r, emg_l = self.settings.emg_right_name, self.settings.emg_left_name
        recs = SensorThreshold.query.filter_by(
            patient_id=pid, week=week, file=night
        ).all()

        def _default() -> Dict[str, int]:
            return {emg_r: 10, emg_l: 10}

        if not recs:
            return _default()

        result = {r.sensor: r.threshold_value for r in recs}
        for s in (emg_r, emg_l):
            result.setdefault(s, 10)
        return result

    def update_threshold(
        self, pid: int, week: str, night: str, sensor: str, payload: Dict[str, Any]
    ) -> Dict[str, str]:
        thr = payload.get("threshold")
        rec = SensorThreshold.query.filter_by(
            patient_id=pid, week=week, file=night, sensor=sensor
        ).first()
        if rec:
            rec.threshold_value = thr
        else:
            rec = SensorThreshold(
                patient_id=pid,
                week=week,
                file=night,
                sensor=sensor,
                threshold_value=thr,
            )
            db.session.add(rec)
        db.session.commit()
        return {"message": "Threshold updated."}

    # 3.3 images --------------------------------------------------------

    def list_images(
        self, pid: int, week: str, night: str, refresh: bool = False
    ) -> List[Dict[str, str]]:
        base = f"{self.settings.downsampled_data_path}/p{pid}_wk{week}/{night[:-4]}200Hz.csv_images"
        if refresh or not os.path.isdir(base):
            self.__generate_images(pid, week, night)
        imgs = [f for f in os.listdir(base) if f.endswith(".png")]
        return [
            {
                "label": (
                    "Whole Night Signal"
                    if "whole_night_signal" in f
                    else f"Sleep Cycle {f.split('_')[2][:-4]}"
                ),
                "src": f"/patients/{pid}/weeks/{week}/nights/{night}/images/{f}",
            }
            for f in imgs
        ]

    def __generate_images(self, pid: int, week: str, night: str) -> None:
        ds = self.settings.downsampled_data_path
        data = pl.read_csv(
            f"{ds}/p{pid}_wk{week}/{night[:-4]}200Hz.csv",
            columns=[self.settings.emg_right_name, self.settings.emg_left_name],
        )
        mr = data.get_column(self.settings.emg_right_name)
        ml = data.get_column(self.settings.emg_left_name)
        preds = EventPrediction.query.filter_by(
            patient_id=pid, week=week, file=night
        ).all()
        generate_night_images(pid, week, night, mr, ml, preds)

    def serve_image(
        self, pid: int, week: str, night: str, image: str
    ) -> Tuple[str, str]:
        folder = f"{self.settings.downsampled_data_path}/p{pid}_wk{week}/{night[:-4]}200Hz.csv_images"
        return folder, image

    # ------------------------------------------------------------------ #
    #   4 · Events
    # ------------------------------------------------------------------ #

    def list_events(self, pid: int, week: str, night: str) -> Dict[str, Any]:
        recs = EventPrediction.query.filter_by(
            patient_id=pid, week=week, file=night
        ).all()
        return {r.name: self.__to_event_dict(r) for r in recs}

    def create_event(
        self, pid: int, week: str, night: str, payload: Dict[str, Any]
    ) -> Dict[str, str]:
        # Direct port of old POST logic (shortened)
        from src.routes import predict_events  # type: ignore

        predict_events(pid, week, night)  # executes old logic
        return {"message": "Event queued / inserted."}

    def patch_event(
        self,
        pid: int,
        week: str,
        night: str,
        eid: str,
        payload: Dict[str, Any],
    ) -> Dict[str, str]:
        event: EventPrediction | None = EventPrediction.query.filter_by(
            patient_id=pid, week=week, file=night, name=eid
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


# ---------------------------------------------------------------------- #
#   Thin wrappers around legacy, procedural code
#   -------------------------------------------------
#   They keep your old algorithms untouched while letting the blueprint
#   call them through the service.
# ---------------------------------------------------------------------- #
def from_routes_get_emg(pid: int, week: str, night: str, idx: float):
    """
    Uses the exact logic from the old `get_emg` function so results stay identical.
    """
    from src.blueprints.routes import get_emg  # noqa: WPS433

    resp, _ = get_emg(pid, week, night, idx)
    return resp
