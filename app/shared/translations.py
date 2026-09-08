"""Modelo de traducciones polimórfico.

El texto multiidioma NO vive en las tablas de cada modelo. Duplicar columnas
(name_es, name_en) obliga a migrar todas las tablas cada vez que se añade un
idioma; esta tabla no.

El español es el idioma base y sigue viviendo en la columna original de cada
modelo. Aquí solo se guardan las traducciones, de modo que un texto sin traducir
cae en el español automáticamente y no en una cadena vacía.
"""
from datetime import datetime

from app.extensions import db
from app.shared.utils import utc_ahora

# Tipos de entidad admitidos en entity_type. No es un enum de BD a propósito:
# añadir un tipo nuevo no debe requerir una migración.
ENTITY_PLACE = "place"
ENTITY_TOUR = "tour"
ENTITY_HISTORICAL = "historical_content"


class Translation(db.Model):
    """Una traducción de un campo de un modelo a un idioma."""

    __tablename__ = 'translations'

    id = db.Column(db.String(36), primary_key=True)

    entity_type = db.Column(db.String(50), nullable=False)   # place, tour, historical_content
    entity_id = db.Column(db.String(36), nullable=False)
    locale = db.Column(db.String(5), nullable=False)         # es, en
    field = db.Column(db.String(50), nullable=False)         # name, description, ...
    value = db.Column(db.Text, nullable=False)

    created_at = db.Column(db.DateTime, default=utc_ahora)
    updated_at = db.Column(db.DateTime, default=utc_ahora, onupdate=utc_ahora)

    __table_args__ = (
        db.UniqueConstraint(
            'entity_type', 'entity_id', 'locale', 'field', name='uq_translation'
        ),
        # El índice cubre exactamente la consulta de lectura: los tres primeros
        # campos del WHERE. El cuarto (field) no entra porque siempre se leen
        # todos los campos de una entidad de golpe.
        db.Index('ix_translation_lookup', 'entity_type', 'entity_id', 'locale'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "entityType": self.entity_type,
            "entityId": self.entity_id,
            "locale": self.locale,
            "field": self.field,
            "value": self.value,
        }
