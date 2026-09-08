"""Resolución de idioma y aplicación de traducciones.

Se llama i18n.py y no locale.py a propósito: un módulo llamado `locale` tapa el
del stdlib, que importa `calendar`, y eso rompe imports en cuanto el archivo
queda en la raíz de un sys.path.
"""
from typing import Any, Dict, List, Optional

from flask import g, request

from app.shared.translations_repository import TranslationRepository

# El contenido se redacta en INGLÉS: es el idioma que vive en las columnas de
# cada modelo y el que se muestra cuando falta una traducción. El español es
# una traducción más, guardada en `translations`.
SUPPORTED_LOCALES = ("en", "es")
DEFAULT_LOCALE = "en"


def parse_accept_language(header: Optional[str]) -> str:
    """Primer idioma soportado que aparece en la cabecera Accept-Language.

    Compara por el prefijo de DOS LETRAS, no por la etiqueta completa: los
    móviles mandan `en-US` o `es-MX` a secas y comparar la etiqueta entera haría
    que un iPhone en inglés recibiera la app en español.

    Respeta el orden del header y devuelve DEFAULT_LOCALE si no hay nada
    soportado. El factor q no se pondera: los clientes que nos importan mandan
    sus preferencias ya ordenadas.
    """
    if not header:
        return DEFAULT_LOCALE

    for entrada in header.split(","):
        etiqueta = entrada.split(";")[0].strip().lower()
        if not etiqueta:
            continue
        if etiqueta == "*":
            return DEFAULT_LOCALE
        if etiqueta[:2] in SUPPORTED_LOCALES:
            return etiqueta[:2]

    return DEFAULT_LOCALE


def current_locale() -> str:
    """Idioma de esta petición.

    Manda la preferencia guardada en la cuenta sobre la cabecera del
    dispositivo: si alguien eligió español en ajustes, quiere español aunque
    tenga el teléfono en inglés. Sin sesión, decide Accept-Language.
    """
    from app.middleware import current_user

    usuario = current_user()
    if usuario is not None and usuario.preferred_locale in SUPPORTED_LOCALES:
        return usuario.preferred_locale

    return getattr(g, "locale", DEFAULT_LOCALE)


def register_locale_middleware(app) -> None:
    """Deja el idioma resuelto en g.locale al principio de cada petición."""

    @app.before_request
    def _resolver_locale():
        g.locale = parse_accept_language(request.headers.get("Accept-Language"))


def apply_translation(
    data: Dict[str, Any],
    entity_type: str,
    locale: str,
    fields: Dict[str, str],
) -> Dict[str, Any]:
    """Traduce UN diccionario ya serializado, in place.

    `fields` mapea el nombre de la columna al de la clave del diccionario,
    p. ej. {"name": "name", "historical_significance": "historicalSignificance"}.

    Un campo sin traducción conserva su valor original: el inglés es el
    fallback, nunca se vacía nada.
    """
    if locale == DEFAULT_LOCALE or not data or not data.get("id"):
        return data

    traducciones = TranslationRepository.find_for_entity(
        entity_type, data["id"], locale
    )
    return _aplicar(data, traducciones, fields)


def apply_translations(
    items: List[Dict[str, Any]],
    entity_type: str,
    locale: str,
    fields: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Traduce una LISTA con una sola consulta.

    Llamar a apply_translation dentro de un bucle daría un N+1: un listado de
    50 sitios haría 51 consultas. Aquí se hace una.
    """
    if locale == DEFAULT_LOCALE or not items:
        return items

    ids = [i["id"] for i in items if i.get("id")]
    por_entidad = TranslationRepository.find_for_entities(entity_type, ids, locale)

    for item in items:
        _aplicar(item, por_entidad.get(item.get("id"), {}), fields)

    return items


def _aplicar(
    data: Dict[str, Any],
    traducciones: Dict[str, str],
    fields: Dict[str, str],
) -> Dict[str, Any]:
    """Vuelca las traducciones sobre el diccionario. Sin consultas."""
    if not traducciones:
        return data

    for columna, clave in fields.items():
        if columna in traducciones:
            data[clave] = traducciones[columna]

    return data
