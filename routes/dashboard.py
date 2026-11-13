from flask import Blueprint, render_template, redirect, url_for
from routes.authentication import login_required

dashboard_views_bp = Blueprint("dashboard_views", __name__)


@dashboard_views_bp.route("/")
def index():
    return redirect(url_for("dashboard_views.dashboard"))


@dashboard_views_bp.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@dashboard_views_bp.route("/live-camera")
@login_required
def live_camera():
    return render_template("live_camera.html")


@dashboard_views_bp.route("/exit-camera")
@login_required
def exit_camera():
    return render_template("exit_camera.html")


@dashboard_views_bp.route("/parking-lot")
@login_required
def parking_lot():
    return render_template("parking_lot.html")


@dashboard_views_bp.route("/anpr-debugger")
@login_required
def anpr_debugger():
    return render_template("anpr_debugger.html")
