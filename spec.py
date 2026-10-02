"""Genera openapi.json y openapi.yaml.

    python spec.py

El documento es la frontera entre backend y frontend. Regenerarlo es barato;
que se quede desactualizado sale caro, así que `tests/test_contract.py` lo
valida contra las respuestas reales del servidor en cada vuelta de la suite.
"""
import decimal
import json
import pathlib
import sys

import yaml

from app.api_spec import build_spec

RAIZ = pathlib.Path(__file__).parent


def _serializable(nodo):
    """Convierte los Decimal del documento en números de JSON.

    Salen de `fields.Decimal` en los schemas de administración, que es el tipo
    correcto para dinero: las tarifas de museo son importes exactos y un float
    los redondea mal. El tipo se queda donde importa —la validación— y solo se
    afloja al escribir el documento, que es texto.
    """
    if isinstance(nodo, decimal.Decimal):
        entero = int(nodo)
        return entero if nodo == entero else float(nodo)
    if isinstance(nodo, dict):
        return {k: _serializable(v) for k, v in nodo.items()}
    if isinstance(nodo, (list, tuple)):
        return [_serializable(x) for x in nodo]
    return nodo


def main():
    documento = _serializable(build_spec().to_dict())

    rutas = len(documento["paths"])
    operaciones = sum(
        1 for p in documento["paths"].values()
        for m in p if m in ("get", "post", "put", "patch", "delete")
    )

    (RAIZ / "openapi.json").write_text(
        json.dumps(documento, indent=2, ensure_ascii=False) + "\n"
    )
    (RAIZ / "openapi.yaml").write_text(
        yaml.safe_dump(documento, sort_keys=False, allow_unicode=True)
    )

    print(f"OK  openapi.json y openapi.yaml — {rutas} rutas, "
          f"{operaciones} operaciones, "
          f"{len(documento['components']['schemas'])} schemas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
