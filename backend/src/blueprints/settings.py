from flask import Blueprint, request
from src.extensions import db
from src.models.settings import Settings

settings_bp = Blueprint("settings", __name__)

@settings_bp.route("/settings", methods=["GET", "POST"])
def settings():
    if request.method == "GET":
        settings = Settings.query.first()
        if settings:
            result = {
                "emgRight": settings.emg_right_name,
                "emgLeft": settings.emg_left_name,
                "ecg": settings.ecg_name,
                "modelFileName": settings.model_file_name,
                "originalDataPath": settings.original_data_path,
                "downsampledDataPath": settings.downsampled_data_path,
                "modelPath": settings.model_path,
                "originalSamplingRate": settings.original_sampling_rate,
                "minimumSamplingRate": settings.minimum_sampling_rate,
            }
        else:
            result = {}
        return result, 200

    if request.method == "POST":
        Settings.query.delete()
        emg_right_name = request.json["emgRight"]
        emg_left_name = request.json["emgLeft"]
        ecg_name = request.json["ecg"]
        model_file_name = request.json["modelFileName"]
        original_data_path = request.json["originalDataPath"]
        downsampled_data_path = request.json["downsampledDataPath"]
        model_path = request.json["modelPath"]
        original_sampling_rate = request.json["originalSamplingRate"]
        minimum_sampling_rate = request.json["minimumSamplingRate"]

        settings = Settings(
            emg_right_name=emg_right_name,
            emg_left_name=emg_left_name,
            ecg_name=ecg_name,
            model_file_name=model_file_name,
            original_data_path=original_data_path,
            downsampled_data_path=downsampled_data_path,
            model_path=model_path,
            original_sampling_rate=original_sampling_rate,
            minimum_sampling_rate=minimum_sampling_rate,
        )
        db.session.add(settings)
        db.session.commit()
        return "Settings updated successfully", 200
