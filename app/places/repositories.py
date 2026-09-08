"""Places repository for database operations"""
from typing import List, Optional, Tuple

from geoalchemy2 import Geography
from sqlalchemy import cast, func

from app.extensions import db
from app.places.models import Place


class PlaceRepository:
    """Repository for Place model operations"""
    
    @staticmethod
    def find_by_id(place_id: str) -> Optional[Place]:
        """Find place by ID"""
        return Place.query.filter_by(id=place_id).first()
    
    @staticmethod
    def find_all(
        skip: int = 0, limit: int = 10, curation: Optional[str] = None
    ) -> Tuple[List[Place], int]:
        """Listado paginado, opcionalmente filtrado por lista editorial.

        `curation` es lo que alimenta las pestañas "Must See" y "Quick Stops"
        de Explore.
        """
        query = Place.query
        if curation:
            query = query.filter(Place.curation == curation)

        total = query.count()
        places = query.order_by(Place.name).offset(skip).limit(limit).all()
        return places, total
    
    @staticmethod
    def find_by_type(place_type: str) -> List[Place]:
        """Find places by type"""
        return Place.query.filter_by(place_type=place_type).all()
    
    @staticmethod
    def _punto(latitude: float, longitude: float):
        """El punto del usuario como geography, listo para comparar con geom."""
        return cast(
            func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326),
            Geography,
        )

    @staticmethod
    def find_nearby(
        user_latitude: float,
        user_longitude: float,
        radius_km: float = 5,
        limit: int = 10
    ) -> List[Place]:
        """Sitios dentro del radio, ordenados por distancia real.

        Lo resuelve PostGIS con el índice GiST. Antes esto traía la tabla
        entera a memoria y calculaba Haversine en Python para cada fila: con
        un puñado de sitios sembrados no se nota, con el catálogo completo de
        la CDMX es el cuello de botella de la pantalla principal.

        Sobre geography, ST_DWithin trabaja en METROS.
        """
        punto = PlaceRepository._punto(user_latitude, user_longitude)

        query = Place.query.filter(
            Place.geom.isnot(None)
        ).filter(
            func.ST_DWithin(Place.geom, punto, float(radius_km) * 1000.0)
        ).order_by(
            func.ST_Distance(Place.geom, punto)
        )

        if limit:
            query = query.limit(limit)

        return query.all()
    
    @staticmethod
    def find_nearby_with_distance(
        user_latitude: float,
        user_longitude: float,
        radius_km: float = 5,
        limit: int = 10,
        curation: Optional[str] = None,
    ) -> List[Tuple[Place, float]]:
        """Como find_nearby, pero devolviendo también la distancia en km.

        La distancia ya la calcula PostGIS para poder ordenar, así que traerla
        de vuelta no cuesta nada — y el diseño la pinta en cada tarjeta
        ("a 800 m de ti"). Pedirla aparte sería una consulta por sitio.
        """
        punto = PlaceRepository._punto(user_latitude, user_longitude)
        distancia = func.ST_Distance(Place.geom, punto)

        query = db.session.query(Place, distancia.label("metros")).filter(
            Place.geom.isnot(None)
        ).filter(
            func.ST_DWithin(Place.geom, punto, float(radius_km) * 1000.0)
        )

        if curation:
            query = query.filter(Place.curation == curation)

        query = query.order_by(distancia)
        if limit:
            query = query.limit(limit)

        return [(fila[0], (fila[1] or 0.0) / 1000.0) for fila in query.all()]

    @staticmethod
    def find_by_location(
        latitude: float,
        longitude: float,
        radius_km: float = 5
    ) -> List[Place]:
        """Todos los sitios del radio, sin tope."""
        return PlaceRepository.find_nearby(latitude, longitude, radius_km, limit=None)

    @staticmethod
    def distance_km(place: Place, latitude: float, longitude: float) -> float:
        """Distancia en km entre un sitio y una coordenada, calculada por PostGIS."""
        punto = PlaceRepository._punto(latitude, longitude)
        metros = db.session.query(
            func.ST_Distance(Place.geom, punto)
        ).filter(Place.id == place.id).scalar()
        return (metros or 0.0) / 1000.0
    
    @staticmethod
    def save(place: Place) -> Place:
        """Save or update a place"""
        db.session.add(place)
        db.session.commit()
        return place
    
    @staticmethod
    def update(place_id: str, data: dict) -> Optional[Place]:
        """Update a place"""
        place = PlaceRepository.find_by_id(place_id)
        if not place:
            return None
        
        for key, value in data.items():
            if hasattr(place, key):
                setattr(place, key, value)
        
        db.session.commit()
        return place
    
    @staticmethod
    def delete(place_id: str) -> bool:
        """Delete a place"""
        place = PlaceRepository.find_by_id(place_id)
        if not place:
            return False
        
        db.session.delete(place)
        db.session.commit()
        return True
