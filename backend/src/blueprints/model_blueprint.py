import logging
from flask import Blueprint

from src.services.model_service import ModelService


class ModelBlueprint:
    def __init__(self) -> None:
        self.__logger = logging.getLogger(__name__)
        self.blueprint = Blueprint(
            "model_blueprint", "model_blueprint", url_prefix="/model"
        )
        self.__model_service = ModelService()
        self.__setup_routes()

    # ------------------------------------------------------------------ #
    #   Route registration
    # ------------------------------------------------------------------ #

    def __setup_routes(self) -> None:

        # --- 1 · Top-level collections --------------------------------------------------
        self.blueprint.add_url_rule(
            "/summary", view_func=self.__get_model_summary, methods=["GET"]
        )
        self.blueprint.add_url_rule(
            "/feature-importance",
            view_func=self.__get_feature_importance,
            methods=["GET"],
        )

    # ------------------------------------------------------------------ #
    #   Handlers  (private “dunder” methods)
    # ------------------------------------------------------------------ #

    def __get_model_summary(self):
        return self.__model_service.get_model_summary(), 200

    def __get_feature_importance(self):
        return self.__model_service.get_feature_importance(), 200
