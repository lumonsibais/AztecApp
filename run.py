"""Application entry point"""
import os
from app import create_app

# Create Flask app
app = create_app(os.getenv("FLASK_ENV", "development"))

if __name__ == "__main__":
    # 0.0.0.0 en lugar del 127.0.0.1 que Flask usa por defecto, por dos razones
    # que aquí son la misma: dentro de un contenedor, escuchar solo en loopback
    # hace que el puerto publicado no lleve a ninguna parte; y para probar la
    # app en un móvil físico, el teléfono entra por la IP del Mac en la wifi.
    #
    # La contrapartida es que el servidor de desarrollo queda visible para
    # quien comparta tu red. Es Flask con datos de prueba, no producción, pero
    # conviene saberlo. Para volver al comportamiento anterior:
    #     HOST=127.0.0.1 python run.py
    app.run(
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
    )
