```python
from typing import Any, Dict, List
from app.shared.translations_repository import TranslationRepository

def apply_translation(data: Dict[str, Any], entity_type: str, locale: str,
                    fields: Dict[str, str]) -> Dict[str, Any]:
    if not data or "id" not in data:
        return data
    translations = TranslationRepository.find_for_entity(entity_type, data["id"], locale)
    for column, key in fields.items():
        if column in translations:
            data[key] = translations[column]
    return data

def apply_translations(items: List[Dict[str, Any]], entity_type: str,
                     locale: str, fields: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not items:
        return items
    entity_ids = [item["id"] for item in items]
    translations = TranslationRepository.find_for_entities(entity_type, entity_ids, locale)
    translation_map = {translation["entity_id"]: translation for translation in translations}
    for item in items:
        item.update(apply_translation(item, entity_type, locale, fields))
    return items
```