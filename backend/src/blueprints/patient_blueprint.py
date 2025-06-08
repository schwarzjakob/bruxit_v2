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

        # --- 1 · Top-level collections --------------------------------------------------
        self.blueprint.add_url_rule(
            "/", view_func=self.__list_patients, methods=["GET"]
        )

        # --- 2 · Weeks ------------------------------------------------------------------
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks",
            "weeks",
            view_func=self.__list_weeks,
            methods=["GET"],
        )
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>",
            "week_summary",
            view_func=self.__week_summary,
            methods=["GET"],
        )

        # --- 3 · Nights / Recordings ----------------------------------------------------
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights",
            "list_nights",
            view_func=self.__list_nights,
            methods=["GET"],
        )
        # Night meta
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>",
            "night_meta",
            view_func=self.__night_meta,
            methods=["GET"],
        )

        # Down-sample
        self.blueprint.add_url_rule(
            "/<int:patient_id>/weeks/<string:week>/nights/<string:night>/downsample",
            view_func=self.__downsample_and_persist_night_recording,
            methods=["POST"],
        )

        # ---- 3.1 metrics & raw signals -----------------------------
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

        # ---- 3.2 thresholds ---------------------------------------
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

        # ---- 3.3 images -------------------------------------------
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

        # --- 5 · Model service ---------------------------------------
        self.blueprint.add_url_rule(
            "/model/feature-importance",
            "feature_importance",
            view_func=self.__feature_importance,
            methods=["GET"],
        )
        self.blueprint.add_url_rule(
            "/model/summary",
            "model_summary",
            view_func=self.__model_summary,
            methods=["GET"],
        )

    # ------------------------------------------------------------------ #
    #   Handlers  (private “dunder” methods)
    # ------------------------------------------------------------------ #

    # 1 · Top-level
    def __list_patients(self):
        return jsonify(self.__patient_service.list_patients()), 200

    # 2 · Weeks
    def __list_weeks(self, patient_id: int):
        return jsonify(self.__patient_service.list_weeks(patient_id)), 200

    def __week_summary(self, patient_id: int, week: str):
        return jsonify(self.__patient_service.week_summary(patient_id, week)), 200

    # 3 · Nights
    def __list_nights(self, patient_id: int, week: str):
        return jsonify(self.__patient_service.list_nights(patient_id, week)), 200

    def __night_meta(self, patient_id: int, week: str, night: str):
        return jsonify(self.__patient_service.night_meta(patient_id, week, night)), 200

    def __downsample_and_persist_night_recording(
        self, patient_id: int, week: str, night: str
    ):
        return (
            self.__patient_service.downsample_and_persist_recording(
                patient_id, week, night
            ),
            202,
        )

    # 3.1 metrics & raw
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
        if data:  # rows already in DB
            return jsonify(data), 200
        return "", 204  # nothing yet

    def __post_sleep_stage(self, patient_id: int, week: str, night: str):
        sampling_rate = int(request.args.get("sampling_rate", 200))

        # heavy compute –  run sync or fire a background job
        created = self.__patient_service.post_sleep_stage(
            patient_id, week, night, sampling_rate
        )
        return ("", 201) if created else ("", 200)

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
    def __events(self, patient_id: int, week: str, night: str):
        if request.method == "GET":
            return (
                jsonify(self.__patient_service.list_events(patient_id, week, night)),
                200,
            )
        body = request.get_json()
        return (
            jsonify(self.__patient_service.create_event(patient_id, week, night, body)),
            201,
        )

    def __patch_event(self, patient_id: int, week: str, night: str, eid: str):
        patch = request.get_json()
        return (
            jsonify(
                self.__patient_service.patch_event(patient_id, week, night, eid, patch)
            ),
            200,
        )

    def __download_events(self):
        directory, fname = self.__patient_service.download_confirmed_events()
        return send_from_directory(directory, fname, as_attachment=True)

    # 5 · Model
    def __feature_importance(self):
        return jsonify(self.__patient_service.feature_importance()), 200

    def __model_summary(self):
        return jsonify(self.__patient_service.model_summary()), 200
