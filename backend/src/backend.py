from flask import Flask, jsonify
from src.config import Config
from src.extensions import db, migrate, cors
from src.blueprints.routes import (
    main,
)  # TODO: Split routes blueprint into respective blueprints
from src.blueprints.auth import auth


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app, resources={r"/*": {"origins": "*"}})

    # register blueprints
    app.register_blueprint(main, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/auth")

    # health check
    @app.route("/health")
    def health():
        return jsonify(status="ok")

    return app


# module-level WSGI app
app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
