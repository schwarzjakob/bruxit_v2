import logging
from flask import Blueprint, request, jsonify, send_from_directory

from src.services.event_service import EventService

logging.basicConfig(level=logging.INFO)


class EventBlueprint:
    def __init__(self) -> None:
        self.__logger = logging.getLogger(__name__)
        self.blueprint = Blueprint(
            "event_blueprint", "event_blueprint", url_prefix="/events"
        )
        self.__event_service = EventService()
        self.__setup_routes()

    def __setup_routes(self) -> None:
        self.blueprint.add_url_rule(
            "/download", view_func=self.__download_events, methods=["GET"]
        )

    def __download_events(self) -> tuple:
        """
        Download all confirmed event predictions as a CSV file.
        """
        self.__logger.info("Fetching all events")
        events_file = self.__event_service.generate_events_file()
        return events_file, 200
