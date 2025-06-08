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
