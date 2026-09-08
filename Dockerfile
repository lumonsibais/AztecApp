# Imagen del backend de AztecApp.
#
# Deliberadamente sin multi-stage: es un proyecto Python puro, no hay nada que
# compilar y separar etapas solo añadiría una capa que mantener.
#
# 3.12 y no 3.11 para que coincida con el venv del Mac: dos versiones distintas
# entre tu máquina y el contenedor es la receta del "en local funciona".
FROM python:3.12-slim

# psycopg2-binary trae su propio libpq, así que no hace falta compilar nada.
# `postgresql-client` sí, para el pg_isready del arranque; `curl` para el
# healthcheck. Nada más: cada paquete extra es superficie que mantener.
RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=run.py

WORKDIR /app

# Las dependencias antes que el código: mientras requirements.txt no cambie,
# Docker reutiliza esta capa y `docker compose build` tarda segundos.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker-entrypoint.sh

EXPOSE 5000

# Se invoca con `bash` explícito en lugar de ejecutar el archivo directamente.
# El compose monta el código como volumen, así que dentro del contenedor manda
# el bit de permisos del checkout del anfitrión y no el que puso el build: si
# git no lo trae marcado como ejecutable, el arranque muere con "permission
# denied". Pasándolo a bash da igual cómo esté el bit.
ENTRYPOINT ["bash", "./docker-entrypoint.sh"]
