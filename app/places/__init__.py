"""Places module initialization and routes"""
from flask import Blueprint

from app.places.controllers import PlaceController

places_bp = Blueprint("places", __name__, url_prefix="/api/places")

# Ojo con el orden: "/saved" va por delante de "/<place_id>". Flask da
# prioridad a las rutas estáticas sobre las que llevan convertidor, así que
# funcionaría igual, pero leerlo en este orden evita sustos al editarlo.
places_bp.route("/saved", methods=["GET"])(PlaceController.get_saved_places)
places_bp.route("/nearby", methods=["GET"])(PlaceController.get_nearby_places)
places_bp.route("/recommended", methods=["GET"])(PlaceController.get_recommended_places)
places_bp.route("/", methods=["GET"])(PlaceController.get_all_places)
places_bp.route("/<place_id>", methods=["GET"])(PlaceController.get_place_detail)
places_bp.route("/<place_id>/save", methods=["POST"])(PlaceController.save_place)
places_bp.route("/<place_id>/save", methods=["DELETE"])(PlaceController.unsave_place)
