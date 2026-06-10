"""Tours controllers"""
from flask import request, jsonify
from app.tours.services import TourService
from app.middleware import token_required
from app.shared.utils import format_response
from app.shared.constants import ERROR_MESSAGES, DEFAULT_LIMIT


class TourController:
    """Controller for tour endpoints"""
    
    @staticmethod
    def get_free_tours():
        """Get free tours available to all users"""
        try:
            tours = TourService.get_free_tours()
            return jsonify(
                format_response(
                    success=True,
                    data={"tours": tours}
                )
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    def get_all_tours():
        """Get all available tours"""
        try:
            page = request.args.get("page", default=1, type=int)
            limit = request.args.get("limit", default=DEFAULT_LIMIT, type=int)
            subscription = request.args.get("subscription", default="free", type=str)
            
            result = TourService.get_all_tours(page, limit, subscription)
            return jsonify(format_response(success=True, data=result)), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    def get_tour_details(tour_id: str):
        """Get detailed information about a tour"""
        try:
            tour = TourService.get_tour_details(tour_id)
            if not tour:
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["NOT_FOUND"])
                ), 404
            
            return jsonify(format_response(success=True, data=tour)), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    @token_required
    def start_tour(current_user, tour_id: str):
        """Start a tour"""
        try:
            progress = TourService.start_tour(tour_id, current_user)
            if not progress:
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["NOT_FOUND"])
                ), 404
            
            return jsonify(
                format_response(
                    success=True,
                    message="Tour started successfully",
                    data={"progressId": progress.id}
                )
            ), 201
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    @token_required
    def update_tour_progress(current_user, tour_id: str):
        """Update progress in a tour"""
        try:
            data = request.get_json()
            progress = TourService.update_tour_progress(tour_id, current_user, data)
            
            if not progress:
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["NOT_FOUND"])
                ), 404
            
            return jsonify(format_response(success=True, data=progress.id)), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    @token_required
    def complete_tour(current_user, tour_id: str):
        """Mark tour as completed"""
        try:
            data = request.get_json() or {}
            progress = TourService.complete_tour(
                tour_id,
                current_user,
                data.get("rating"),
                data.get("notes")
            )
            
            if not progress:
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["NOT_FOUND"])
                ), 404
            
            return jsonify(
                format_response(success=True, message="Tour completed!")
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    @token_required
    def get_user_tours(current_user):
        """Get all tours started by user"""
        try:
            tours = TourService.get_user_tours(current_user)
            return jsonify(
                format_response(success=True, data={"tours": tours})
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
