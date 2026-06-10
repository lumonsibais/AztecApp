"""Places API controllers"""
from flask import request, jsonify
from app.places.services import PlaceService
from app.shared.utils import format_response
from app.shared.constants import ERROR_MESSAGES, DEFAULT_LIMIT


class PlaceController:
    """Controller for place endpoints"""
    
    @staticmethod
    def get_nearby_places():
        """Get places near user's current location"""
        try:
            latitude = request.args.get("latitude", type=float)
            longitude = request.args.get("longitude", type=float)
            radius = request.args.get("radius", default=5, type=float)
            subscription_tier = request.args.get("subscription", default="free", type=str)
            
            if latitude is None or longitude is None:
                return jsonify(
                    format_response(
                        success=False,
                        error="Missing latitude or longitude"
                    )
                ), 400
            
            places = PlaceService.get_nearby_places(
                latitude,
                longitude,
                radius,
                subscription_tier
            )
            
            return jsonify(
                format_response(
                    success=True,
                    data={
                        "places": [p.to_dict() for p in places],
                        "count": len(places),
                    }
                )
            ), 200
        
        except Exception as e:
            return jsonify(
                format_response(
                    success=False,
                    error=str(e)
                )
            ), 500
    
    @staticmethod
    def get_all_places():
        """Get all places with pagination"""
        try:
            page = request.args.get("page", default=1, type=int)
            limit = request.args.get("limit", default=DEFAULT_LIMIT, type=int)
            place_type = request.args.get("type", default=None, type=str)
            subscription_tier = request.args.get("subscription", default="free", type=str)
            
            result = PlaceService.get_all_places(
                page,
                limit,
                place_type,
                subscription_tier
            )
            
            return jsonify(format_response(success=True, data=result)), 200
        
        except Exception as e:
            return jsonify(
                format_response(success=False, error=str(e))
            ), 500
    
    @staticmethod
    def get_place_detail(place_id: str):
        """Get detailed information about a specific place"""
        try:
            place = PlaceService.get_place_details(place_id)
            
            if not place:
                return jsonify(
                    format_response(
                        success=False,
                        error=ERROR_MESSAGES["NOT_FOUND"]
                    )
                ), 404
            
            return jsonify(format_response(success=True, data=place)), 200
        
        except Exception as e:
            return jsonify(
                format_response(success=False, error=str(e))
            ), 500
    
    @staticmethod
    def get_recommended_places():
        """Get recommended places based on user location"""
        try:
            latitude = request.args.get("latitude", type=float)
            longitude = request.args.get("longitude", type=float)
            subscription_tier = request.args.get("subscription", default="free", type=str)
            limit = request.args.get("limit", default=10, type=int)
            
            if latitude is None or longitude is None:
                return jsonify(
                    format_response(
                        success=False,
                        error="Missing latitude or longitude"
                    )
                ), 400
            
            places = PlaceService.get_recommended_places(
                latitude,
                longitude,
                subscription_tier,
                limit
            )
            
            return jsonify(
                format_response(
                    success=True,
                    data={
                        "places": places,
                        "count": len(places),
                    }
                )
            ), 200
        
        except Exception as e:
            return jsonify(
                format_response(success=False, error=str(e))
            ), 500
