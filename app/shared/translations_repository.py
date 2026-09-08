"""Repositorio de traducciones."""
import uuid
from typing import Dict, List, Optional

from app.extensions import db
from app.shared.translations import Translation


class TranslationRepository:
    """Acceso a la tabla translations."""

    @staticmethod
    def find_for_entity(entity_type: str, entity_id: str, locale: str) -> Dict[str, str]:
        """Todas las traducciones de UNA entidad: {campo: valor}."""
        filas = Translation.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id,
            locale=locale,
        ).all()

        return {t.field: t.value for t in filas}

    @staticmethod
    def find_for_entities(
        entity_type: str,
        entity_ids: List[str],
        locale: str,
    ) -> Dict[str, Dict[str, str]]:
        """Traducciones de VARIAS entidades en una sola consulta.

        Devuelve {entity_id: {campo: valor}}.

        El acumulador importa: una entidad tiene varias filas (una por campo) y
        una comprensión de diccionario directa se queda solo con la última, de
        modo que un sitio con nombre y descripción traducidos perdería uno de
        los dos sin dar ningún error.
        """
        if not entity_ids:
            return {}

        filas = Translation.query.filter_by(
            entity_type=entity_type,
            locale=locale,
        ).filter(
            Translation.entity_id.in_(entity_ids)
        ).all()

        resultado: Dict[str, Dict[str, str]] = {}
        for t in filas:
            resultado.setdefault(t.entity_id, {})[t.field] = t.value

        return resultado

    @staticmethod
    def upsert(
        entity_type: str,
        entity_id: str,
        locale: str,
        field: str,
        value: str,
    ) -> Translation:
        """Crea o actualiza una traducción. La unique constraint la respalda."""
        fila = Translation.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id,
            locale=locale,
            field=field,
        ).first()

        if fila:
            fila.value = value
        else:
            fila = Translation(
                id=str(uuid.uuid4()),
                entity_type=entity_type,
                entity_id=entity_id,
                locale=locale,
                field=field,
                value=value,
            )
            db.session.add(fila)

        db.session.commit()
        return fila

    @staticmethod
    def delete_for_entity(entity_type: str, entity_id: str) -> int:
        """Borra las traducciones de una entidad. Para cuando se borra el sitio.

        No hay foreign key hacia cada tabla porque la tabla es polimórfica, así
        que la limpieza es responsabilidad de quien borra.
        """
        borradas = Translation.query.filter_by(
            entity_type=entity_type,
            entity_id=entity_id,
        ).delete(synchronize_session=False)
        db.session.commit()
        return borradas
