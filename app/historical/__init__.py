"""Historical content module initialization and routes"""
from flask import Blueprint
from app.historical.controllers import (
    HistoricalContentController,
    TimelineController,
    LakeViewController,
)

historical_bp = Blueprint("historical", __name__, url_prefix="/api/historical")

# Historical content routes
historical_bp.route("/content", methods=["GET"])(HistoricalContentController.get_all_content)
historical_bp.route("/content/<content_id>", methods=["GET"])(HistoricalContentController.get_content_detail)
historical_bp.route("/content/place/<place_id>", methods=["GET"])(HistoricalContentController.get_content_by_place)
historical_bp.route("/content/era", methods=["GET"])(HistoricalContentController.get_content_by_era)

# Timeline routes
historical_bp.route("/timelines", methods=["GET"])(TimelineController.get_all_timelines)

# Lake view routes
historical_bp.route("/lake-view", methods=["GET"])(LakeViewController.get_lake_data)
