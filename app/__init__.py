"""Main Flask application factory"""
from flask import Flask, jsonify
from flask_cors import CORS
from app.config import get_config
from app.extensions import db, migrate, jwt, cors
from app.shared.utils import format_response
from app.shared.constants import ERROR_MESSAGES
from app.shared.i18n import register_locale_middleware

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

    # Un token revocado (logout) deja de valer aunque no haya expirado.
    # El import va dentro de la función para no crear un ciclo con app.users.
    @jwt.token_in_blocklist_loader
    def _token_revoked(jwt_header, jwt_payload):
        from app.users.services import UserService
        return UserService.is_token_revoked(jwt_payload["jti"])

    # Idioma de la petición: deja g.locale listo antes de cualquier handler.
    register_locale_middleware(app)

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
    
    # El esquema se gestiona con Alembic (Flask-Migrate): `flask db upgrade`.
    # db.create_all() aquí competía con las migraciones y creaba las tablas
    # saltándose el control de versiones del esquema.

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
