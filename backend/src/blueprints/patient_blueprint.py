import logging
from flask import Blueprint, request, jsonify, send_from_directory

from src.services.patient_service import PatientService


class PatientBlueprint:
    """
    Exposes all patient-related REST resources.

    URL hierarchy
    -------------
    /patients
        /{patientId}
            /data
            /weeks
                /{week}
                    /nights
                        /{nightId}
                            /maximum_voluntary_contraction
                            /duration
                            /sleep_stage
                            /emg_windows
                                /{five_minute_window_index}
                            /thresholds
                                /{sensor}
                            /images
                                /{imageName}
                            /downsample
                            /events
                                /{eventId}
    """

    def __init__(self) -> None:
        self.__logger = logging.getLogger(__name__)
        self.blueprint = Blueprint(
            "patient_blueprint", "patient_blueprint", url_prefix="/patients"
        )
        self.__patient_service = PatientService()
        self.__setup_routes()

    # ------------------------------------------------------------------ #
    #   Route registration
    # ------------------------------------------------------------------ #

    def __setup_routes(self) -> None:

        self.blueprint.add_url_rule(
            "/", view_func=self.__get_patients, methods=["GET"]
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/downsample",
            view_func=self.__downsample_and_persist_night_recording,
            methods=["POST"],
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/duration",
            view_func=self.__get_night_duration,
            methods=["GET"],
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/maximum_voluntary_contraction",
            view_func=self.__get_night_maximum_voluntary_contraction,
            methods=["GET"],
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/emg_windows/<float:five_minute_window_index>",
            view_func=self.__get_emg_window,
            methods=["GET"],
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/sleep_stage",
            view_func=self.__get_sleep_stage,
            methods=["GET"],
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/sleep_stage",
            view_func=self.__post_sleep_stage,
            methods=["POST"],
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/thresholds",
            view_func=self.__get_thresholds,
            methods=["GET"],
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/thresholds",
            view_func=self.__post_threshold,
            methods=["POST"],
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/images",
            view_func=self.__get_night_images,
            methods=["GET"],
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/images/<string:image>",
            view_func=self.__get_night_image,
            methods=["GET"],
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/events",
            view_func=self.__get_events,
            methods=["GET"],
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/events",
            view_func=self.__post_event,
            methods=["POST"],
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/events/<string:event_name>",
            view_func=self.__patch_event,
            methods=["PATCH"],
        )

    # ------------------------------------------------------------------ #
    #   Handlers  (private “dunder” methods)
    # ------------------------------------------------------------------ #

    def __get_patients(self):
        return jsonify(self.__patient_service.list_patients()), 200

    def __downsample_and_persist_night_recording(
        self, patient_id: int, week: str, night: str
    ):
        return (
            self.__patient_service.downsample_and_persist_recording(
                patient_id, week, night
            ),
            202,
        )

    def __get_night_maximum_voluntary_contraction(
        self, patient_id: int, week: str, night: str
    ):
        return (
            self.__patient_service.get_night_maximum_voluntary_contraction(
                patient_id, week, night
            ),
            200,
        )

    def __get_night_duration(self, patient_id: int, week: str, night: str):
        return self.__patient_service.get_night_duration(patient_id, week, night), 200

    def __get_emg_window(
        self, patient_id: int, week: str, night: str, five_minute_window_index: float
    ):
        return (
            self.__patient_service.get_emg_window(
                patient_id, week, night, five_minute_window_index
            ),
            200,
        )

    def __get_sleep_stage(self, patient_id: int, week: str, night: str):
        data = self.__patient_service.fetch_sleep_stage(patient_id, week, night)
        if data:
            return jsonify(data), 200
        return "", 204

    def __post_sleep_stage(self, patient_id: int, week: str, night: str):
        sampling_rate = int(request.args.get("sampling_rate", 200))
        sleep_stage_segments = self.__patient_service.generate_sleep_stage_segments(
            patient_id, week, night, sampling_rate
        )
        return ("", 201) if sleep_stage_segments else ("", 200)

    # 3.2 thresholds
    def __get_thresholds(self, patient_id: int, week: str, night: str):
        return (
            jsonify(self.__patient_service.get_thresholds(patient_id, week, night)),
            200,
        )

    def __post_threshold(self, patient_id: int, week: str, night: str):
        payload = request.get_json()
        sensor = payload.get("sensor")
        return (
            jsonify(
                self.__patient_service.post_threshold(
                    patient_id, week, night, sensor, payload
                )
            ),
            200,
        )

    # 3.3 images
    def __get_night_images(self, patient_id: int, week: str, night: str):
        refresh = request.args.get("refresh", "false").lower() == "true"
        return (
            self.__patient_service.get_night_images(patient_id, week, night, refresh),
            200,
        )

    def __get_night_image(self, patient_id: int, week: str, night: str, image: str):
        directory, filename = self.__patient_service.get_night_image(
            patient_id, week, night, image
        )
        return send_from_directory(directory, filename)

    # 4 · Events
    def __get_events(self, patient_id: int, week: str, night: str):
        if not self.__patient_service.get_events(patient_id, week, night):
            return {}, 204
        return self.__patient_service.get_events(patient_id, week, night), 200

    def __post_event(self, patient_id: int, week: str, night: str):
        event_details = request.get_json()
        return (
            self.__patient_service.create_event(patient_id, week, night, event_details),
            201,
        )

    def __patch_event(self, patient_id: int, week: str, night: str, event_name: str):
        patch_data = request.get_json()
        result = self.__patient_service.patch_event(
            patient_id, week, night, event_name, patch_data
        )
        if "error" in result:
            return result, 404
        return result, 200
