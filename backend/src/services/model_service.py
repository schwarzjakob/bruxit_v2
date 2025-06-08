import logging
import xgboost as xgb
from flask import jsonify

from src.utils.utils import get_settings

logging.basicConfig(level=logging.INFO)


class ModelService:
    def __init__(self):
        self.__logger = logging.getLogger(__name__)

    def get_model_summary(self):
        model_file_name = get_settings().model_file_name
        model_path = get_settings().model_path

        model = xgb.XGBClassifier()
        model.load_model(f"{model_path}/{model_file_name}")

        params = model.get_params()
        print(params)
        print(jsonify(params))
        return jsonify(params)

    def get_feature_importance(self):
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
