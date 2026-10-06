"""Controladores de la API de administración."""
from flask import current_app, jsonify, request
from marshmallow import ValidationError

from app.admin.schemas import (
    contenido_actualizar_schema,
    contenido_crear_schema,
    lake_geometria_schema,
    place_actualizar_schema,
    place_crear_schema,
    tour_actualizar_schema,
    tour_crear_schema,
)
from app.admin.services import (
    AdminContenidoService,
    AdminLagoService,
    AdminPlaceService,
    AdminTourService,
    NoExiste,
    ReferenciaRota,
    YaExiste,
)
from app.middleware import requires_admin
from app.shared.constants import ERROR_MESSAGES
from app.shared.utils import format_response


def _validacion(err: ValidationError):
    return jsonify(format_response(
        success=False,
        error=ERROR_MESSAGES["VALIDATION_ERROR"],
        details=err.messages,
    )), 400


def _conflicto(mensaje: str):
    return jsonify(format_response(success=False, error=mensaje)), 409


def _no_encontrado():
    return jsonify(
        format_response(success=False, error=ERROR_MESSAGES["NOT_FOUND"])
    ), 404


def _error_servidor(exc: Exception):
    current_app.logger.exception("Error en la API de administración: %s", exc)
    return jsonify(
        format_response(success=False, error=ERROR_MESSAGES["INTERNAL_ERROR"])
    ), 500


def _cuerpo():
    return request.get_json(silent=True) or {}


class AdminPlaceController:

    @staticmethod
    @requires_admin
    def listar(current_user):
        """Todo el catálogo, borradores incluidos.

        Al revés que el listado público: lo primero que necesita ver quien
        carga contenido es lo que tiene a medias.
        """
        try:
            places = AdminPlaceService.listar()
            return jsonify(format_response(success=True, data={
                "places": [p.to_dict(include_full_details=True) for p in places],
                "count": len(places),
                "drafts": sum(1 for p in places if not p.is_published),
            })), 200
        except Exception as e:
            return _error_servidor(e)

    @staticmethod
    @requires_admin
    def crear(current_user):
        try:
            datos = place_crear_schema.load(_cuerpo())
            place = AdminPlaceService.crear(datos)
            return jsonify(format_response(
                success=True,
                message="Place created",
                data=place.to_dict(include_full_details=True),
            )), 201
        except ValidationError as err:
            return _validacion(err)
        except YaExiste as e:
            return _conflicto(f"Ya existe un sitio con el id '{e}'")
        except Exception as e:
            return _error_servidor(e)

    @staticmethod
    @requires_admin
    def actualizar(current_user, place_id: str):
        try:
            datos = place_actualizar_schema.load(_cuerpo())
            place = AdminPlaceService.actualizar(place_id, datos)
            return jsonify(format_response(
                success=True,
                message="Place updated",
                data=place.to_dict(include_full_details=True),
            )), 200
        except ValidationError as err:
            return _validacion(err)
        except NoExiste:
            return _no_encontrado()
        except Exception as e:
            return _error_servidor(e)


class AdminTourController:

    @staticmethod
    @requires_admin
    def listar(current_user):
        try:
            tours = AdminTourService.listar()
            return jsonify(format_response(success=True, data={
                "tours": [t.to_dict(include_stops=True) for t in tours],
                "count": len(tours),
            })), 200
        except Exception as e:
            return _error_servidor(e)

    @staticmethod
    @requires_admin
    def crear(current_user):
        try:
            datos = tour_crear_schema.load(_cuerpo())
            tour = AdminTourService.crear(datos)
            return jsonify(format_response(
                success=True,
                message="Tour created",
                data=tour.to_dict(include_stops=True),
            )), 201
        except ValidationError as err:
            return _validacion(err)
        except YaExiste as e:
            return _conflicto(f"Ya existe un tour con el id '{e}'")
        except ReferenciaRota as e:
            return _conflicto(str(e))
        except Exception as e:
            return _error_servidor(e)

    @staticmethod
    @requires_admin
    def actualizar(current_user, tour_id: str):
        try:
            datos = tour_actualizar_schema.load(_cuerpo())
            tour = AdminTourService.actualizar(tour_id, datos)
            return jsonify(format_response(
                success=True,
                message="Tour updated",
                data=tour.to_dict(include_stops=True),
            )), 200
        except ValidationError as err:
            return _validacion(err)
        except NoExiste:
            return _no_encontrado()
        except ReferenciaRota as e:
            return _conflicto(str(e))
        except Exception as e:
            return _error_servidor(e)


class AdminContenidoController:

    @staticmethod
    @requires_admin
    def listar(current_user):
        try:
            contenidos = AdminContenidoService.listar()
            return jsonify(format_response(success=True, data={
                "content": [c.to_dict() for c in contenidos],
                "count": len(contenidos),
            })), 200
        except Exception as e:
            return _error_servidor(e)

    @staticmethod
    @requires_admin
    def crear(current_user):
        try:
            datos = contenido_crear_schema.load(_cuerpo())
            contenido = AdminContenidoService.crear(datos)
            return jsonify(format_response(
                success=True,
                message="Content created",
                data=contenido.to_dict(),
            )), 201
        except ValidationError as err:
            return _validacion(err)
        except YaExiste as e:
            return _conflicto(f"Ya existe un artículo con el id '{e}'")
        except ReferenciaRota as e:
            return _conflicto(str(e))
        except Exception as e:
            return _error_servidor(e)

    @staticmethod
    @requires_admin
    def actualizar(current_user, content_id: str):
        try:
            datos = contenido_actualizar_schema.load(_cuerpo())
            contenido = AdminContenidoService.actualizar(content_id, datos)
            return jsonify(format_response(
                success=True,
                message="Content updated",
                data=contenido.to_dict(),
            )), 200
        except ValidationError as err:
            return _validacion(err)
        except NoExiste:
            return _no_encontrado()
        except ReferenciaRota as e:
            return _conflicto(str(e))
        except Exception as e:
            return _error_servidor(e)


class AdminLagoController:

    @staticmethod
    @requires_admin
    def listar(current_user):
        try:
            year = request.args.get("year", type=int)
            filas = AdminLagoService.listar(year)
            return jsonify(format_response(success=True, data={
                "geometries": [
                    {
                        "id": f.id,
                        "name": f.name,
                        "surfaceType": f.surface_type,
                        "yearEstimate": f.year_estimate,
                        "tenochtitlanName": f.tenochtitlan_name,
                        "description": f.description,
                    }
                    for f in filas
                ],
                "count": len(filas),
            })), 200
        except Exception as e:
            return _error_servidor(e)

    @staticmethod
    @requires_admin
    def crear(current_user):
        try:
            datos = lake_geometria_schema.load(_cuerpo())
            fila = AdminLagoService.crear(datos)
            return jsonify(format_response(
                success=True,
                message="Geometry created",
                data={"id": fila.id, "name": fila.name,
                      "surfaceType": fila.surface_type},
            )), 201
        except ValidationError as err:
            return _validacion(err)
        except Exception as e:
            # ST_GeomFromGeoJSON rechaza geometrías que el schema no puede
            # comprobar —un polígono que se cruza a sí mismo, por ejemplo—.
            # Eso es culpa del trazado, no del servidor: 400, no 500.
            if "GeoJSON" in str(e) or "geometry" in str(e).lower():
                from app.extensions import db
                db.session.rollback()
                return jsonify(format_response(
                    success=False,
                    error="PostGIS rechazó la geometría",
                    details=str(e)[:300],
                )), 400
            return _error_servidor(e)

    @staticmethod
    @requires_admin
    def borrar(current_user, geometria_id: str):
        try:
            if not AdminLagoService.borrar(geometria_id):
                return _no_encontrado()
            return jsonify(format_response(
                success=True, message="Geometry deleted")), 200
        except Exception as e:
            return _error_servidor(e)
