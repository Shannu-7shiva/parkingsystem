import os
import sys
import logging
from pathlib import Path
from flask import Flask, send_from_directory, jsonify, render_template

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from database.database import init_db, close_db
from database.seed import seed_database
from routes.authentication import auth_bp
from routes.dashboard import dashboard_views_bp
from routes.vehicles import vehicles_views_bp
from routes.analytics import analytics_views_bp
from routes.api import api_bp


_logging_configured = False

def configure_logging():
    """Sets up unified logging to file and console."""
    global _logging_configured
    if _logging_configured:
        return
    _logging_configured = True

    log_format = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
    log_file = config.LOGS_DIR / "application.log"

    root_logger = logging.getLogger()
    if not root_logger.handlers:
        root_logger.setLevel(logging.INFO)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(logging.Formatter(log_format))
        root_logger.addHandler(sh)
        try:
            fh = logging.FileHandler(str(log_file), encoding="utf-8")
            fh.setFormatter(logging.Formatter(log_format))
            root_logger.addHandler(fh)
        except Exception:
            pass


def create_app():
    """Application factory for Smart Parking Management System."""
    configure_logging()
    logger = logging.getLogger("app")

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )

    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.config["UPLOAD_FOLDER"] = str(config.UPLOAD_FOLDER)

    # Initialize DB schema & seed default data if not present
    try:
        init_db()
        seed_database(reset=False)
    except Exception as e:
        logger.warning(f"Database initialization note: {e}")

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_views_bp)
    app.register_blueprint(vehicles_views_bp)
    app.register_blueprint(analytics_views_bp)
    app.register_blueprint(api_bp)

    # Serve uploads securely
    @app.route("/uploads/<path:subpath>")
    def serve_upload(subpath):
        return send_from_directory(str(config.UPLOAD_FOLDER), subpath)

    # Teardown database session
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        close_db(exception)

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("base.html", error_title="404 - Page Not Found", error_message="The requested parking portal page does not exist."), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"Internal server error encountered: {e}")
        return jsonify({"success": False, "error": "Internal Server Error occurred. Please check logs."}), 500

    logger.info("Smart Parking ANPR application initialized successfully.")
    return app


app = create_app()

if __name__ == "__main__":
    print(f"\n=======================================================")
    print(f" SMART PARKING MANAGEMENT SYSTEM USING ANPR")
    print(f" Starting server at http://{config.HOST}:{config.PORT}")
    print(f" Admin Login: Username: admin | Password: admin123")
    print(f"=======================================================\n")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG_MODE)
