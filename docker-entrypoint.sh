#!/usr/bin/env bash
# Arranque del backend dentro del contenedor.
#
# Tres pasos, en este orden y por esta razón:
#
#   1. Esperar a Postgres. `depends_on: healthy` del compose ya lo cubre, pero
#      un contenedor que se reinicia solo puede adelantarse a la base.
#   2. Aplicar migraciones. Siempre: es idempotente y evita el clásico "a mí me
#      funciona" de quien no se acordó de correrlas.
#   3. Sembrar SOLO si la base está vacía. Si ya hay sitios, el seed no se toca:
#      volver a sembrar encima de datos que alguien estuvo probando es la forma
#      más rápida de perder una tarde de pruebas.
set -euo pipefail

: "${DATABASE_URL:?falta DATABASE_URL}"

echo "==> esperando a la base de datos"
for intento in $(seq 1 60); do
  if pg_isready -d "$DATABASE_URL" > /dev/null 2>&1; then
    echo "    lista (intento $intento)"
    break
  fi
  if [ "$intento" -eq 60 ]; then
    echo "ERROR: la base no respondió en 60 intentos" >&2
    exit 1
  fi
  sleep 1
done

echo "==> aplicando migraciones"
flask db upgrade

echo "==> comprobando si hace falta sembrar"
YA_HAY=$(python - <<'PY'
from app import create_app, db
from app.places.models import Place

app = create_app()
with app.app_context():
    print(db.session.query(Place).count())
PY
)

if [ "$YA_HAY" = "0" ]; then
  echo "    base vacía: sembrando datos de prueba"
  python seed.py
else
  echo "    ya hay $YA_HAY sitios: no toco nada"
fi

echo "==> backend en marcha en el puerto 5000"
exec python run.py
