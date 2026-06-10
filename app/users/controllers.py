"""Users controllers"""
from flask import request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token
from app.users.services import UserService
from app.middleware import token_required
from app.shared.utils import format_response, is_valid_email
from app.shared.constants import ERROR_MESSAGES


class UserController:
    """Controller for user endpoints"""
    
    @staticmethod
    def register():
        """Register a new user"""
        try:
            data = request.get_json()
            
            email = data.get("email")
            password = data.get("password")
            first_name = data.get("firstName")
            last_name = data.get("lastName")
            
            # Validation
            if not email or not password:
                return jsonify(
                    format_response(
                        success=False,
                        error="Email and password required"
                    )
                ), 400
            
            if not is_valid_email(email):
                return jsonify(
                    format_response(success=False, error="Invalid email format")
                ), 400
            
            if len(password) < 8:
                return jsonify(
                    format_response(
                        success=False,
                        error="Password must be at least 8 characters"
                    )
                ), 400
            
            user = UserService.register_user(email, password, first_name, last_name)
            if not user:
                return jsonify(
                    format_response(
                        success=False,
                        error=ERROR_MESSAGES["EMAIL_EXISTS"]
                    )
                ), 409
            
            # Create tokens
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            
            return jsonify(
                format_response(
                    success=True,
                    message="User registered successfully",
                    data={
                        "user": user.to_dict(),
                        "accessToken": access_token,
                        "refreshToken": refresh_token,
                    }
                )
            ), 201
        
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    def login():
        """Login user"""
        try:
            data = request.get_json()
            email = data.get("email")
            password = data.get("password")
            
            if not email or not password:
                return jsonify(
                    format_response(success=False, error="Email and password required")
                ), 400
            
            user = UserService.verify_credentials(email, password)
            if not user:
                return jsonify(
                    format_response(
                        success=False,
                        error=ERROR_MESSAGES["INVALID_CREDENTIALS"]
                    )
                ), 401
            
            # Create tokens
            access_token = create_access_token(identity=user.id)
            refresh_token = create_refresh_token(identity=user.id)
            
            return jsonify(
                format_response(
                    success=True,
                    message="Login successful",
                    data={
                        "user": user.to_dict(),
                        "accessToken": access_token,
                        "refreshToken": refresh_token,
                    }
                )
            ), 200
        
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    @token_required
    def get_profile(current_user):
        """Get user profile"""
        try:
            profile = UserService.get_user_profile(current_user)
            if not profile:
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["USER_NOT_FOUND"])
                ), 404
            
            return jsonify(format_response(success=True, data=profile)), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    @token_required
    def update_profile(current_user):
        """Update user profile"""
        try:
            data = request.get_json()
            user = UserService.update_user_profile(current_user, data)
            
            if not user:
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["USER_NOT_FOUND"])
                ), 404
            
            return jsonify(
                format_response(success=True, message="Profile updated", data=user.to_dict())
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
    
    @staticmethod
    @token_required
    def handle_location_permission(current_user):
        """Handle location permission request"""
        try:
            data = request.get_json()
            response = data.get("response")  # "granted" or "denied"
            context = data.get("context")
            
            if response not in ["granted", "denied"]:
                return jsonify(
                    format_response(success=False, error="Invalid response")
                ), 400
            
            success = UserService.handle_location_permission(current_user, response, context)
            
            if not success:
                return jsonify(
                    format_response(success=False, error=ERROR_MESSAGES["USER_NOT_FOUND"])
                ), 404
            
            return jsonify(
                format_response(
                    success=True,
                    message="Location permission recorded"
                )
            ), 200
        except Exception as e:
            return jsonify(format_response(success=False, error=str(e))), 500
