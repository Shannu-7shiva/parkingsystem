from flask import Blueprint, render_template
from routes.authentication import login_required

vehicles_views_bp = Blueprint("vehicles_views", __name__)


@vehicles_views_bp.route("/vehicles")
@login_required
def vehicles():
    return render_template("vehicles.html")


@vehicles_views_bp.route("/vehicles/<plate>")
@login_required
def vehicle_details(plate):
    return render_template("vehicle_details.html", plate_number=plate)


@vehicles_views_bp.route("/parking-history")
@login_required
def parking_history():
    return render_template("parking_history.html")


@vehicles_views_bp.route("/blacklist")
@login_required
def blacklist():
    return render_template("blacklist.html")


@vehicles_views_bp.route("/settings")
@login_required
def settings():
    return render_template("settings.html")
