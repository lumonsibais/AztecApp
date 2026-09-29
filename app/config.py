"""Flask application configuration"""
import os
from datetime import timedelta


class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = False
    TESTING = False
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/aztec_explorer"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-secret-key-change-in-production")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=90)
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
    
    # Pagination
    DEFAULT_PAGE_SIZE = 10
    MAX_PAGE_SIZE = 100
    
    # File uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    
    # Third-party services
    GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")

    # ---------------------------------------------------------------
    # Cobro desde las tiendas
    # ---------------------------------------------------------------
    # El desbloqueo se compra dentro de la app, así que quien cobra es Apple o
    # Google y el servidor solo verifica recibos. Nada de esto tiene valor por
    # defecto: sin credenciales, /payments/confirm responde 402 diciendo que el
    # cobro no está configurado, que es mejor que conceder accesos a ciegas.

    # App Store. La clave es un .p8 de App Store Connect (Users and Access ->
    # Integrations -> In-App Purchase). Se descarga UNA sola vez.
    APPLE_BUNDLE_ID = os.getenv("APPLE_BUNDLE_ID", "")
    APPLE_ISSUER_ID = os.getenv("APPLE_ISSUER_ID", "")
    APPLE_KEY_ID = os.getenv("APPLE_KEY_ID", "")
    APPLE_PRIVATE_KEY = os.getenv("APPLE_PRIVATE_KEY", "")        # contenido del .p8
    APPLE_PRIVATE_KEY_PATH = os.getenv("APPLE_PRIVATE_KEY_PATH", "")
    APPLE_PRODUCT_ID = os.getenv("APPLE_PRODUCT_ID", "")

    # Aceptar compras de sandbox. Hace falta encendido para probar con cuentas
    # de prueba y DURANTE LA REVISIÓN de Apple, porque el revisor compra en
    # sandbox contra el binario de producción. Apagado en el servidor de
    # producción una vez publicada la app: si no, un recibo de sandbox —que
    # cualquiera puede generarse gratis— desbloquea la app de verdad.
    APPLE_ALLOW_SANDBOX = (
        os.getenv("APPLE_ALLOW_SANDBOX", "").lower() in ("1", "true", "yes")
    )

    # Google Play. La cuenta de servicio se crea en Google Cloud y se le da
    # acceso a la app en Play Console; necesita permiso para ver datos
    # financieros o la API de compras responde 401.
    GOOGLE_PACKAGE_NAME = os.getenv("GOOGLE_PACKAGE_NAME", "")
    GOOGLE_PRODUCT_ID = os.getenv("GOOGLE_PRODUCT_ID", "")
    GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    GOOGLE_SERVICE_ACCOUNT_PATH = os.getenv("GOOGLE_SERVICE_ACCOUNT_PATH", "")

    # Secreto opcional en la URL de los webhooks de las tiendas. No es lo que
    # los protege —eso lo hace no fiarse del cuerpo de la notificación—, solo
    # evita que un curioso nos haga consultar la API de las tiendas a su gusto.
    STORE_WEBHOOK_SECRET = os.getenv("STORE_WEBHOOK_SECRET", "")

    # Puerta de desarrollo del cobro. Con esto en true, /payments/confirm
    # concede el acceso SIN comprobar el recibo contra el proveedor, que es lo
    # único que permite probar la app desbloqueada mientras no haya pasarela.
    #
    # Fuera de tu máquina va en false y no se discute: con esto encendido,
    # cualquiera se desbloquea la app mandando un identificador inventado.
    #
    # El valor por defecto es false a propósito. Que haya que encenderlo a mano
    # es la mitad de la protección.
    PAYMENTS_ALLOW_UNVERIFIED = (
        os.getenv("PAYMENTS_ALLOW_UNVERIFIED", "").lower() in ("1", "true", "yes")
    )
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    # El echo de SQLAlchemy imprime cada SELECT entero: útil cuando se depura
    # una consulta, ilegible el resto del tiempo. Se enciende con
    # SQLALCHEMY_ECHO=1 en lugar de venir siempre puesto.
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "").lower() in ("1", "true", "yes")


class TestingConfig(Config):
    """Testing configuration.

    Los tests corren contra PostgreSQL con PostGIS, no contra SQLite. No es una
    preferencia: las columnas Geography de Place y LakeGeometry no existen en
    SQLite y `db.create_all()` revienta con "near POINT: syntax error". Probar
    contra un motor distinto al de producción tampoco valía de mucho.

    Levanta la base con `docker compose up -d db`; conftest crea la base de
    test y habilita la extensión.
    """
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql://aztec:aztec@localhost:5432/aztec_explorer_test",
    )


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env: str = None):
    """Get configuration based on environment"""
    if env is None:
        env = os.getenv("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)
