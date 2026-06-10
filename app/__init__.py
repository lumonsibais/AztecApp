"""Main Flask application factory"""
from flask import Flask, jsonify
from flask_cors import CORS
from app.config import get_config
from app.extensions import db, migrate, jwt, cors
from app.shared.utils import format_response
from app.shared.constants import ERROR_MESSAGES

# Import blueprints
from app.places import places_bp
from app.tours import tours_bp
from app.users import users_bp
from app.payments import payments_bp
from app.historical import historical_bp


def create_app(config_env: str = None):
    """Application factory"""
    
    # Create Flask app
    app = Flask(__name__)
    
    # Load configuration
    config = get_config(config_env)
    app.config.from_object(config)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config['CORS_ORIGINS']}})
    
    # Register blueprints
    app.register_blueprint(places_bp)
    app.register_blueprint(tours_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(historical_bp)
    
    # Health check endpoint
    @app.route("/health", methods=["GET"])
    def health():
        return jsonify(format_response(
            success=True,
            message="Aztec Explorer API is running"
        )), 200
    
    # Global error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify(format_response(
            success=False,
            error=ERROR_MESSAGES["NOT_FOUND"]
        )), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify(format_response(
            success=False,
            error=ERROR_MESSAGES["INTERNAL_ERROR"]
        )), 500
    
    # Create tables
    with app.app_context():
        db.create_all()
    
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
