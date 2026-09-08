"""Users module initialization and routes"""
from flask import Blueprint
from app.users.controllers import UserController

users_bp = Blueprint("users", __name__, url_prefix="/api/users")

# Routes
users_bp.route("/register", methods=["POST"])(UserController.register)
users_bp.route("/login", methods=["POST"])(UserController.login)
users_bp.route("/refresh", methods=["POST"])(UserController.refresh)
users_bp.route("/logout", methods=["POST"])(UserController.logout)
users_bp.route("/profile", methods=["GET"])(UserController.get_profile)
users_bp.route("/profile", methods=["PUT"])(UserController.update_profile)
users_bp.route("/location-permission", methods=["POST"])(UserController.handle_location_permission)
