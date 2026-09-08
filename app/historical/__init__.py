"""Historical content module initialization and routes"""
from flask import Blueprint

from app.historical.controllers import (
    HistoricalContentController,
    LakeViewController,
    TimelineController,
)

historical_bp = Blueprint("historical", __name__, url_prefix="/api/historical")

# Guía histórica — las dos pestañas del diseño
historical_bp.route("/chronology", methods=["GET"])(HistoricalContentController.get_chronology)
historical_bp.route("/topics", methods=["GET"])(HistoricalContentController.get_topics)

# Contenido
historical_bp.route("/content", methods=["GET"])(HistoricalContentController.get_all_content)
historical_bp.route("/content/topic", methods=["GET"])(HistoricalContentController.get_content_by_topic)
historical_bp.route("/content/era", methods=["GET"])(HistoricalContentController.get_content_by_era)
historical_bp.route("/content/place/<place_id>", methods=["GET"])(HistoricalContentController.get_content_by_place)
historical_bp.route("/content/<content_id>", methods=["GET"])(HistoricalContentController.get_content_detail)

# Progreso de lectura — el botón "Mark read"
historical_bp.route("/content/<content_id>/read", methods=["POST"])(HistoricalContentController.mark_read)
historical_bp.route("/content/<content_id>/read", methods=["DELETE"])(HistoricalContentController.unmark_read)

# Cronologías
historical_bp.route("/timelines", methods=["GET"])(TimelineController.get_all_timelines)

# Overlay del lago
historical_bp.route("/lake-view", methods=["GET"])(LakeViewController.get_lake_data)
