import io
import logging
import pandas as pd
from flask import make_response

from src.models.event_prediction import EventPrediction


class EventService:
    def __init__(self):
        self.__logger = logging.getLogger(__name__)

    def generate_events_file(self):
        """
        Generate a file containing all confirmed event predictions.
        """
        # Create a pandas DataFrame with your data
        predictions = EventPrediction.query.filter_by(confirmed=True)
        prediction_data = []

        for prediction in predictions:
            prediction_data.append(
                {
                    "patient_id": prediction.patient_id,
                    "week": prediction.week,
                    "file": prediction.file,
                    "name": prediction.name,
                    "start_s": prediction.start_s,
                    "end_s": prediction.end_s,
                    "std_mr": prediction.std_mr,
                    "std_ml": prediction.std_ml,
                    "var_mr": prediction.var_mr,
                    "var_ml": prediction.var_ml,
                    "rms_mr": prediction.rms_mr,
                    "rms_ml": prediction.rms_ml,
                    "mav_mr": prediction.mav_mr,
                    "mav_ml": prediction.mav_ml,
                    "log_det_mr": prediction.log_det_mr,
                    "log_det_ml": prediction.log_det_ml,
                    "wl_mr": prediction.wl_mr,
                    "wl_ml": prediction.wl_ml,
                    "aac_mr": prediction.aac_mr,
                    "aac_ml": prediction.aac_ml,
                    "dasdv_mr": prediction.dasdv_mr,
                    "dasdv_ml": prediction.dasdv_ml,
                    "wamp_mr": prediction.wamp_mr,
                    "wamp_ml": prediction.wamp_ml,
                    "fr_mr": prediction.fr_mr,
                    "fr_ml": prediction.fr_ml,
                    "mnp_mr": prediction.mnp_mr,
                    "mnp_ml": prediction.mnp_ml,
                    "tot_mr": prediction.tot_mr,
                    "tot_ml": prediction.tot_ml,
                    "mnf_mr": prediction.mnf_mr,
                    "mnf_ml": prediction.mnf_ml,
                    "mdf_mr": prediction.mdf_mr,
                    "mdf_ml": prediction.mdf_ml,
                    "pkf_mr": prediction.pkf_mr,
                    "pkf_ml": prediction.pkf_ml,
                    "HRV_mean": prediction.HRV_mean,
                    "HRV_median": prediction.HRV_median,
                    "HRV_sdnn": prediction.HRV_sdnn,
                    "HRV_min": prediction.HRV_min,
                    "HRV_max": prediction.HRV_max,
                    "HRV_vhf": prediction.HRV_vhf,
                    "HRV_lf": prediction.HRV_lf,
                    "HRV_hf": prediction.HRV_hf,
                    "HRV_lf_hf": prediction.HRV_lf_hf,
                    "RRI": prediction.RRI,
                    "y_prob": prediction.y_prob,
                    "confirmed": prediction.confirmed,
                    "sensor": prediction.sensor,
                    "event_type": prediction.event_type,
                    "status": prediction.status,
                    "justification": prediction.justification,
                }
            )

        predictions_df = pd.DataFrame(prediction_data)
        predictions_df = predictions_df.sort_values(
            by=["patient_id", "week", "file", "name"]
        )

        predictions_df = pd.DataFrame(prediction_data)
        predictions_df = predictions_df.sort_values(
            by=["patient_id", "week", "file", "name"]
        )

        # Save the DataFrame to a CSV file in-memory (not on disk)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            predictions_df.to_excel(writer, index=False, sheet_name="Confirmed Events")

        output.seek(0)

        # Create a response with the CSV file and set appropriate headers
        events_file = make_response(output.getvalue())
        events_file.headers["Content-Disposition"] = (
            "attachment; filename=confirmed_events.xlsx"
        )
        events_file.headers["Content-Type"] = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        return events_file
