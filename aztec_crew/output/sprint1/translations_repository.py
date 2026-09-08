```python
import uuid
from typing import Dict, List
from app.extensions import db
from app.shared.translations import Translation

class TranslationRepository:
    @staticmethod
    def find_for_entity(entity_type: str, entity_id: str, locale: str) -> Dict[str, str]:
        rows = Translation.query.filter_by(entity_type=entity_type, entity_id=entity_id, locale=locale).all()
        return {t.field: t.value for t in rows}

    @staticmethod
    def find_for_entities(entity_type: str, entity_ids: List[str], locale: str) -> Dict[str, Dict[str, str]]:
        if not entity_ids:
            return {}
        rows = Translation.query.filter_by(entity_type=entity_type, locale=locale).filter(Translation.entity_id.in_(entity_ids)).all()
        return {t.entity_id: {t.field: t.value} for t in rows}

    @staticmethod
    def upsert(entity_type: str, entity_id: str, locale: str, field: str, value: str) -> Translation:
        existing = Translation.query.filter_by(entity_type=entity_type, entity_id=entity_id, locale=locale, field=field).first()
        if existing:
            existing.value = value
        else:
            existing = Translation(id=str(uuid.uuid4()), entity_type=entity_type, entity_id=entity_id, locale=locale, field=field, value=value)
            db.session.add(existing)
        db.session.commit()
        return existing
```