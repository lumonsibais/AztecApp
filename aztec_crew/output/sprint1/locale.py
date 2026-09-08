```python
from flask import g, request

SUPPORTED_LOCALES = ("es", "en")
DEFAULT_LOCALE = "es"

def parse_accept_language(header: str) -> str:
    if not header:
        return DEFAULT_LOCALE
    for lang in header.split(","):
        lang = lang.split(";")[0].strip()
        if lang in SUPPORTED_LOCALES:
            return lang
    return DEFAULT_LOCALE

def current_locale() -> str:
    return getattr(g, "locale", DEFAULT_LOCALE)

def register_locale_middleware(app) -> None:
    @app.before_request
    def set_locale():
        g.locale = parse_accept_language(request.headers.get("Accept-Language"))
```