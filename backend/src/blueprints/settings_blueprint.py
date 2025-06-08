import logging
from flask import Blueprint, request, jsonify
from src.services.settings_service import SettingsService


class SettingsBlueprint:
    def __init__(self):
        self.__logger = logging.getLogger(__name__)
        self.blueprint = Blueprint(
            "settings_blueprint", "settings_blueprint", url_prefix="/settings"
        )
        self.__service = SettingsService()
        self.__setup_routes()

    def __setup_routes(self):
        self.blueprint.add_url_rule(
            "/", view_func=self.__get_settings, methods=["GET"], strict_slashes=False
        )
        self.blueprint.add_url_rule(
            "/", view_func=self.__set_settings, methods=["POST"], strict_slashes=False
        )

    def __get_settings(self):
        settings, status = self.__service.get_settings()
        return jsonify(settings), status

    def __set_settings(self):
        updated = self.__service.set_settings(request)
        return jsonify(updated), 200
