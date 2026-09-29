"""API de administración del catálogo.

Bajo `/api/admin` y no mezclada con las rutas públicas, por tres razones:

  1. La frontera de seguridad se ve de un vistazo. Un POST colgando de
     `/api/places/` obliga a mirar el decorador de cada función para saber
     quién puede llamarlo; un prefijo entero dice lo mismo desde la URL.
  2. Se puede cerrar desde fuera. El día que esto salga de una máquina de
     desarrollo, `/api/admin/*` se bloquea en el proxy con una regla, sin
     tocar código.
  3. Los dos contratos tienen vidas distintas. El público está congelado y lo
     consume la app; este lo consumimos nosotros y va a cambiar cada vez que
     cargar contenido resulte incómodo.

No hay borrado de sitios, tours ni artículos, y es deliberado: algo que
alguien guardó en favoritos o que forma parte de un recorrido no debe poder
desaparecer de golpe. Se retiran con `is_published` o con `status`, que
conserva lo que apunta a ellos. El único borrado real es el de los polígonos
del lago, que no tienen nada colgando.
"""
from flask import Blueprint

from app.admin.controllers import (
    AdminContenidoController,
    AdminLagoController,
    AdminPlaceController,
    AdminTourController,
)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# `endpoint=` explícito en todas. Flask nombra el endpoint con el nombre de la
# función, y aquí los cuatro controladores tienen un método `listar`: sin esto
# la app ni siquiera arranca ("View function mapping is overwriting an existing
# endpoint function"). Nombrarlos a mano además deja los nombres legibles en
# url_map, que es lo que lee el test de cobertura del contrato.

# Sitios
admin_bp.route("/places", methods=["GET"],
               endpoint="listar_places")(AdminPlaceController.listar)
admin_bp.route("/places", methods=["POST"],
               endpoint="crear_place")(AdminPlaceController.crear)
admin_bp.route("/places/<place_id>", methods=["PUT"],
               endpoint="actualizar_place")(AdminPlaceController.actualizar)

# Tours, con sus paradas en la misma llamada
admin_bp.route("/tours", methods=["GET"],
               endpoint="listar_tours")(AdminTourController.listar)
admin_bp.route("/tours", methods=["POST"],
               endpoint="crear_tour")(AdminTourController.crear)
admin_bp.route("/tours/<tour_id>", methods=["PUT"],
               endpoint="actualizar_tour")(AdminTourController.actualizar)

# Guía histórica
admin_bp.route("/content", methods=["GET"],
               endpoint="listar_contenido")(AdminContenidoController.listar)
admin_bp.route("/content", methods=["POST"],
               endpoint="crear_contenido")(AdminContenidoController.crear)
admin_bp.route("/content/<content_id>", methods=["PUT"],
               endpoint="actualizar_contenido")(AdminContenidoController.actualizar)

# Polígonos del overlay del lago
admin_bp.route("/lake-geometries", methods=["GET"],
               endpoint="listar_lago")(AdminLagoController.listar)
admin_bp.route("/lake-geometries", methods=["POST"],
               endpoint="crear_lago")(AdminLagoController.crear)
admin_bp.route("/lake-geometries/<geometria_id>", methods=["DELETE"],
               endpoint="borrar_lago")(AdminLagoController.borrar)
