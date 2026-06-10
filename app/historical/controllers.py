"""Historical content controllers"""
from flask import request, jsonify
from app.historical.services import (
    HistoricalContentService,
    TimelineService,
    LakeViewService,
)
from app.shared.utils import format_response
from app.shared.constants import ERROR_MESSAGES


class HistoricalContentController:
    """Controller for historical content"""
    
    @staticmethod
    def get_content_by_place(place_id: str):
        """Get historical content for a place"""
        try:
            content = HistoricalContentService.get_content_by_place(place_id)
            return jsonify(
                format_response(success=True, data={"content": content})
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    def get_content_by_era():
        """Get content by historical era"""
        try:
            era = request.args.get("era", type=str)
            if not era:
                return jsonify(
                    format_response(success=False, error="Era parameter required")
                ), 400
            
            content = HistoricalContentService.get_content_by_era(era)
            return jsonify(
                format_response(success=True, data={"content": content})
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    def get_all_content():
        """Get all historical content"""
        try:
            content_type = request.args.get("type", default=None, type=str)
            content = HistoricalContentService.get_all_content(content_type)
            return jsonify(
                format_response(success=True, data={"content": content})
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    def get_content_detail(content_id: str):
        """Get detailed content"""
        try:
            content = HistoricalContentService.get_content_detail(content_id)
            if not content:
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["NOT_FOUND"])
                ), 404
            
            return jsonify(format_response(success=True, data=content)), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500


class TimelineController:
    """Controller for timelines"""
    
    @staticmethod
    def get_all_timelines():
        """Get all timelines"""
        try:
            timelines = TimelineService.get_all_timelines()
            return jsonify(
                format_response(success=True, data={"timelines": timelines})
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500


class LakeViewController:
    """Controller for lake view overlays"""
    
    @staticmethod
    def get_lake_data():
        """Get lake overlay data for a location"""
        try:
            latitude = request.args.get("latitude", type=float)
            longitude = request.args.get("longitude", type=float)
            radius = request.args.get("radius", default=5, type=float)
            
            if latitude is None or longitude is None:
                return jsonify(
                    format_response(success=False, error="Missing coordinates")
                ), 400
            
            lake_data = LakeViewService.get_lake_data(latitude, longitude, radius)
            return jsonify(
                format_response(
                    success=True,
                    data={"lakeData": lake_data}
                )
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
