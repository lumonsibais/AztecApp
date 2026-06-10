"""Tours module initialization and routes"""
from flask import Blueprint
from app.tours.controllers import TourController

tours_bp = Blueprint("tours", __name__, url_prefix="/api/tours")

# Routes
tours_bp.route("/free", methods=["GET"])(TourController.get_free_tours)
tours_bp.route("/", methods=["GET"])(TourController.get_all_tours)
tours_bp.route("/<tour_id>", methods=["GET"])(TourController.get_tour_details)
tours_bp.route("/<tour_id>/start", methods=["POST"])(TourController.start_tour)
tours_bp.route("/<tour_id>/progress", methods=["PUT"])(TourController.update_tour_progress)
tours_bp.route("/<tour_id>/complete", methods=["POST"])(TourController.complete_tour)
tours_bp.route("/user/tours", methods=["GET"])(TourController.get_user_tours)
