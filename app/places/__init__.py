"""Places module initialization and routes"""
from flask import Blueprint
from app.places.controllers import PlaceController

places_bp = Blueprint("places", __name__, url_prefix="/api/places")

# Routes
places_bp.route("/nearby", methods=["GET"])(PlaceController.get_nearby_places)
places_bp.route("/", methods=["GET"])(PlaceController.get_all_places)
places_bp.route("/recommended", methods=["GET"])(PlaceController.get_recommended_places)
places_bp.route("/<place_id>", methods=["GET"])(PlaceController.get_place_detail)
