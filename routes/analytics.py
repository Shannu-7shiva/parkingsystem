from flask import Blueprint, render_template
from routes.authentication import login_required

analytics_views_bp = Blueprint("analytics_views", __name__)


@analytics_views_bp.route("/analytics")
@login_required
def analytics():
    return render_template("analytics.html")
