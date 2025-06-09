import os
from flask import Flask, jsonify
from src.config import Config
from src.extensions import db, migrate, cors, duckdb_instance

from src.blueprints.settings_blueprint import SettingsBlueprint
from src.blueprints.patient_blueprint import PatientBlueprint
from src.blueprints.event_blueprint import EventBlueprint
from src.blueprints.model_blueprint import ModelBlueprint

# TODO: Add logging utility for entire application
# TODO: Investigate utils.py
# TODO: Investigate ssd.py and rename it (e.g. sleep_stage_service.py)
# TODO: Migrate to polars entirely


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        duckdb_instance.init_app(app)

    cors.init_app(app, resources={r"/*": {"origins": "*"}})

    settings_blueprint = SettingsBlueprint()
    patient_blueprint = PatientBlueprint()
    event_blueprint = EventBlueprint()
    model_blueprint = ModelBlueprint()

    # register blueprints
    app.register_blueprint(settings_blueprint.blueprint)
    app.register_blueprint(patient_blueprint.blueprint)
    app.register_blueprint(event_blueprint.blueprint)
    app.register_blueprint(model_blueprint.blueprint)

    # health check
    @app.route("/health")
    def health():
        return jsonify(status="ok")

    return app


# module-level WSGI app
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
