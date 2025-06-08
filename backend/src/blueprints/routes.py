from flask import Blueprint, request, send_from_directory, abort, jsonify, make_response
from src.extensions import db
from src.models.event_prediction import EventPrediction
from src.models.maximum_voluntary_contraction import MaximumVoluntaryContraction
from src.models.night_duration import NightDuration
from src.models.sensor_threshold import SensorThreshold
from src.models.settings import Settings
from src.models.sleep_stage_segment import SleepStageSegment

from src.utils.utils import *
from src.ssd import *
import psycopg2
from psycopg2.extras import execute_values
import time
import io
from sqlalchemy import create_engine
import time
import xgboost as xgb
import joblib
import pandas as pd
import polars as pl
from sklearn.preprocessing import MinMaxScaler
import openpyxl

main = Blueprint("main", __name__)


@main.route(
    "/confirmed-events/<int:patient_id>/<string:week>/<string:file>", methods=["PATCH"]
)
def patch_confirmed_events(patient_id, week, file):
    update = request.json
    print(update)

    prediction_to_update = EventPrediction.query.filter_by(
        patient_id=patient_id, week=week, file=file, name=update["name"]
    ).first()

    if (prediction_to_update.start_s != update["start_s"]) or (
        prediction_to_update.end_s != update["end_s"]
    ):
        print("update status because of different start or end")
        prediction_to_update.status = "modified"

    prediction_to_update.start_s = update["start_s"]
    prediction_to_update.end_s = update["end_s"]
    prediction_to_update.confirmed = update["confirmed"]

    # Change y_pred?

    db.session.commit()

    return "Confirmation of event updated successfully.", 200


@main.route(
    "/prediction-sensors/<int:patient_id>/<string:week>/<string:file>",
    methods=["PATCH"],
)
def patch_prediction_sensors(patient_id, week, file):
    emg_right_name = get_settings().emg_right_name  # 'MR'
    emg_left_name = get_settings().emg_left_name  # 'ML'

    update = request.json
    print(update)
    sensor = update["sensor"]

    if set(sensor) == set([emg_left_name]):
        sensor = emg_left_name
    if set(sensor) == set([emg_right_name]):
        sensor = emg_right_name
    if set(sensor) == set([emg_left_name, emg_right_name]):
        sensor = "both"

    prediction_to_update = EventPrediction.query.filter_by(
        patient_id=patient_id, week=week, file=file, name=update["name"]
    ).first()
    prediction_to_update.sensor = sensor
    db.session.commit()

    return "Sensor updated successfully.", 200


@main.route(
    "/justification/<int:patient_id>/<string:week>/<string:file>", methods=["PATCH"]
)
def patch_justification(patient_id, week, file):
    update = request.json
    print(update)
    name = update["name"]
    justification = update["justification"]

    justification_to_update = EventPrediction.query.filter_by(
        patient_id=patient_id, week=week, file=file, name=name
    ).first()
    justification_to_update.justification = justification
    db.session.commit()

    return "Justification updated successfully.", 200


@main.route(
    "/prediction-event-type/<int:patient_id>/<string:week>/<string:file>",
    methods=["PATCH"],
)
def patch_prediction_event_type(patient_id, week, file):
    update = request.json
    print(update)
    event_type = update["event_type"]

    prediction_to_update = EventPrediction.query.filter_by(
        patient_id=patient_id, week=week, file=file, name=update["name"]
    ).first()
    prediction_to_update.event_type = event_type
    db.session.commit()

    return "Event type updated successfully.", 200


@main.route(
    "/image/<int:patient_id>/<string:week>/<string:file>/<string:img>", methods=["GET"]
)
def serve_image(patient_id, week, file, img):
    downsampled_data_path = get_settings().downsampled_data_path

    folder_path = (
        downsampled_data_path + f"/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv_images/"
    )
    print(folder_path + img)
    if os.path.exists(folder_path + img):
        return send_from_directory(folder_path, img)
    else:
        return abort(404)  # File not found


@main.route(
    "/predict-events/<int:patient_id>/<string:week>/<string:file>",
    methods=["GET", "POST"],
)
def predict_events(patient_id, week, file):
    predictions = EventPrediction.query.filter_by(
        patient_id=patient_id, week=week, file=file
    ).all()
    print(predictions)

    if request.method == "GET":
        downsampled_data_path = get_settings().downsampled_data_path
        model_path = get_settings().model_path

        minimum_sampling_rate = get_settings().minimum_sampling_rate  # 200

        model_file_name = get_settings().model_file_name

        if not predictions:

            if os.path.isfile(
                f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv"
            ):
                features = pd.read_csv(
                    f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv"
                )

                times = features.iloc[:, 1:3]
                features = features.iloc[:, 3:43]

            else:
                sensor_data = pd.read_csv(
                    f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz.csv"
                )
                features = extract_features_for_prediction(
                    sensor_data, sampling_rate=minimum_sampling_rate
                )
                print("Writing features to csv")

                features.to_csv(
                    f"{downsampled_data_path}/p{patient_id}_wk{week}/{file[:-4]}200Hz_features.csv"
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

            print(f"Predicted class labels for new data: {y_pred}")

            print(f"Predicted probabilities for new data: {y_pred_proba}")

            unique, counts = np.unique(y_pred, return_counts=True)

            print(f"EventPrediction: {dict(zip(unique, counts))}")

            result = pd.concat([times, features], axis=1)
            result["y"] = y_pred
            result["y_prob"] = [max(p) for p in y_pred_proba]

            # print(result)

            predictions = result[result["y"] == 1]
            predictions["confirmed"] = True

            print(predictions)

            predictions_with_features = aggregate_events(predictions)

            for key in predictions_with_features:
                prediction_db = EventPrediction(
                    patient_id=patient_id,
                    week=week,
                    file=file,
                    name=key,
                    start_s=predictions_with_features[key]["start_s"],
                    end_s=predictions_with_features[key]["end_s"],
                    std_mr=predictions_with_features[key]["std_mr"].item(),
                    std_ml=predictions_with_features[key]["std_ml"].item(),
                    var_mr=predictions_with_features[key]["var_mr"].item(),
                    var_ml=predictions_with_features[key]["var_ml"].item(),
                    rms_mr=predictions_with_features[key]["rms_mr"].item(),
                    rms_ml=predictions_with_features[key]["rms_ml"].item(),
                    mav_mr=predictions_with_features[key]["mav_mr"].item(),
                    mav_ml=predictions_with_features[key]["mav_ml"].item(),
                    log_det_mr=predictions_with_features[key]["log_det_mr"].item(),
                    log_det_ml=predictions_with_features[key]["log_det_ml"].item(),
                    wl_mr=predictions_with_features[key]["wl_mr"].item(),
                    wl_ml=predictions_with_features[key]["wl_ml"].item(),
                    aac_mr=predictions_with_features[key]["aac_mr"].item(),
                    aac_ml=predictions_with_features[key]["aac_ml"].item(),
                    dasdv_mr=predictions_with_features[key]["dasdv_mr"].item(),
                    dasdv_ml=predictions_with_features[key]["dasdv_ml"].item(),
                    wamp_mr=predictions_with_features[key]["wamp_mr"].item(),
                    wamp_ml=predictions_with_features[key]["wamp_ml"].item(),
                    fr_mr=predictions_with_features[key]["fr_mr"].item(),
                    fr_ml=predictions_with_features[key]["fr_ml"].item(),
                    mnp_mr=predictions_with_features[key]["mnp_mr"].item(),
                    mnp_ml=predictions_with_features[key]["mnp_ml"].item(),
                    tot_mr=predictions_with_features[key]["tot_mr"].item(),
                    tot_ml=predictions_with_features[key]["tot_ml"].item(),
                    mnf_mr=predictions_with_features[key]["mnf_mr"].item(),
                    mnf_ml=predictions_with_features[key]["mnf_ml"].item(),
                    mdf_mr=predictions_with_features[key]["mdf_mr"].item(),
                    mdf_ml=predictions_with_features[key]["mdf_ml"].item(),
                    pkf_mr=predictions_with_features[key]["pkf_mr"].item(),
                    pkf_ml=predictions_with_features[key]["pkf_ml"].item(),
                    HRV_mean=predictions_with_features[key]["HRV_mean"].item(),
                    HRV_median=predictions_with_features[key]["HRV_median"].item(),
                    HRV_sdnn=predictions_with_features[key]["HRV_sdnn"].item(),
                    HRV_min=predictions_with_features[key]["HRV_min"].item(),
                    HRV_max=predictions_with_features[key]["HRV_max"].item(),
                    HRV_vhf=predictions_with_features[key]["HRV_vhf"].item(),
                    HRV_lf=predictions_with_features[key]["HRV_lf"].item(),
                    HRV_hf=predictions_with_features[key]["HRV_hf"].item(),
                    HRV_lf_hf=predictions_with_features[key]["HRV_lf_hf"].item(),
                    RRI=predictions_with_features[key]["RRI"].item(),
                    y_prob=predictions_with_features[key]["y_prob"].item(),
                    confirmed=True,
                    sensor="both",
                    event_type="",
                    status="model",
                    justification="",
                )

                db.session.add(prediction_db)

            db.session.commit()

            return predictions_with_features, 200
        else:
            result = {}
            for prediction in predictions:
                result[prediction.name] = {
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

            return result, 200

    if request.method == "POST":
        emg_right_name = get_settings().emg_right_name  # 'MR'
        emg_left_name = get_settings().emg_left_name  # 'ML'

        event_info = request.json
        print(event_info)

        start_s = float(event_info["start_s"])
        end_s = float(event_info["end_s"])
        event_type = event_info["event_type"]

        sensor = event_info["sensor"]

        if set(sensor) == set([emg_left_name]):
            sensor = emg_left_name
        if set(sensor) == set([emg_right_name]):
            sensor = emg_right_name
        if set(sensor) == set([emg_left_name, emg_right_name]):
            sensor = "both"

        justification = event_info["justification"]
        print(start_s, end_s, justification)

        # Calculate metrics
        metrics = get_new_event_metrics(patient_id, week, file, start_s, end_s)

        print(metrics)

        # Get new event name and rename others
        if not predictions:
            print("Add prediction with name e1")
            name = "e1"

            add_new_prediction(
                patient_id,
                week,
                file,
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
                    EventPrediction.file == file,
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
                    file,
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
                        EventPrediction.file == file,
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
                    file,
                    start_s,
                    end_s,
                    event_type,
                    sensor,
                    justification,
                    name,
                    metrics,
                )

        return "Post event added by expert.", 200


# Feature importance (assuming you have trained with feature names)
@main.route("/model-feature-importance", methods=["GET"])
def get_feature_importance():
    model_file_name = get_settings().model_file_name
    model_path = get_settings().model_path

    model = xgb.XGBClassifier()
    model.load_model(f"{model_path}/{model_file_name}")

    importance = (
        model.feature_importances_
    )  # Use feature_importances_ from XGBClassifier
    feature_names = model.get_booster().feature_names
    feature_importance = sorted(
        zip(feature_names, importance.tolist()), key=lambda x: x[1], reverse=True
    )

    print(feature_importance)
    print(jsonify(feature_importance))
    return jsonify(feature_importance)


# Model summary information (e.g., model parameters)
@main.route("/model-summary", methods=["GET"])
def get_model_summary():
    model_file_name = get_settings().model_file_name
    model_path = get_settings().model_path

    model = xgb.XGBClassifier()
    model.load_model(f"{model_path}/{model_file_name}")

    params = model.get_params()  # Gets model parameters
    print(params)
    print(jsonify(params))
    return jsonify(params)
