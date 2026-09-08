# Levantar el backend y probar el front

## El camino corto

Desde `AztecApp/`:

```bash
docker compose up
```

Eso levanta Postgres con PostGIS, aplica las migraciones, siembra datos de
prueba **si la base está vacía** y deja la API en **`http://localhost:5001`**.

> **Ojo con el puerto: es el 5001, no el 5000.** El 5000 ya lo tiene la API de
> iBet en esta máquina, y en macOS también se lo queda AirPlay Receiver desde
> Monterey. Dentro del contenedor la app sigue en el 5000 de siempre; solo
> cambia el puerto que se publica al Mac.

La primera vez tarda un par de minutos construyendo la imagen; las siguientes,
segundos. Cuando veas esto ya está listo:

```
aztec_api  | ==> backend en marcha en el puerto 5000
```

Compruébalo:

```bash
curl -s http://localhost:5001/api/places/ | head -c 200
```

Y ahora el front, desde `AztecAppFrontend/`:

```bash
flutter create --platforms=ios,android --project-name aztec_app .   # solo la 1ª vez
flutter pub get
flutter run --dart-define=API_BASE=http://localhost:5001
```

## A qué dirección apunta el front

Esta es la parte que hace perder media hora, así que va aparte:

| Dónde corre la app | `API_BASE` | Por qué |
|---|---|---|
| Simulador de iOS | `http://localhost:5001` | Comparte red con el Mac |
| Emulador de Android | `http://10.0.2.2:5001` | `localhost` es el emulador, no tu Mac |
| iPhone o Android físico | `http://<IP-de-tu-Mac>:5001` | El móvil entra por la wifi |
| macOS de escritorio | `http://localhost:5001` | — |

Tu IP en la wifi:

```bash
ipconfig getifaddr en0
```

El móvil tiene que estar en la misma red que el Mac. El backend ya escucha en
`0.0.0.0`, así que no hay nada más que tocar.

En Android, además, el tráfico HTTP en claro viene bloqueado por defecto desde
Android 9. Si la app no conecta pero el `curl` sí, es eso: en
`android/app/src/main/AndroidManifest.xml`, dentro de `<application>`, añade
`android:usesCleartextTraffic="true"`. Es para desarrollo; en producción todo
irá por HTTPS y esa línea se quita.

## Trabajar en el front sin backend

Si solo estás moviendo pantallas, no hace falta ni base de datos:

```bash
docker compose --profile mock up mock
```

El mock del contrato queda en `http://localhost:4010` sirviendo ejemplos
generados desde `openapi.json`. La app no nota la diferencia: los dos hablan el
mismo contrato.

```bash
flutter run --dart-define=API_BASE=http://localhost:4010
```

Lo que el mock **no** hace es lógica: siempre devuelve el mismo ejemplo, no
guarda nada y no comprueba contraseñas. Sirve para maquetar, no para probar
flujos.

## En español

```bash
flutter run --dart-define=API_BASE=http://localhost:5001 --dart-define=LOCALE=es-MX
```

El backend compara por prefijo de dos letras, así que `es-MX` resuelve a
español. El contenido base está en inglés y el español entra por la tabla de
traducciones; lo que no esté traducido cae al inglés en vez de venir vacío.

## Comandos que vas a necesitar

```bash
docker compose up -d              # en segundo plano
docker compose logs -f api        # ver qué hace el backend
docker compose restart api        # reiniciar solo la API
docker compose down               # parar todo (los datos se conservan)
docker compose down -v            # parar Y BORRAR la base — vuelve a sembrar al subir
docker compose build --no-cache   # reconstruir tras cambiar requirements.txt
```

El código va montado como volumen, así que al guardar un archivo Flask recarga
solo: **no hace falta reconstruir** para cambiar código Python. Solo si tocas
`requirements.txt`.

## Probar el desbloqueo de 15 USD

En local, `PAYMENTS_ALLOW_UNVERIFIED` está en `true` y `/confirm` concede el
acceso sin pasarela. Sirve para ver la app con todo desbloqueado:

```bash
TOKEN=$(curl -s -X POST http://localhost:5001/api/users/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"yo@az.com","password":"testpassword123"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["accessToken"])')

curl -s -X POST http://localhost:5001/api/payments/confirm \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"provider":"stripe","externalId":"pi_prueba"}'
```

En cualquier entorno que no sea tu máquina, esa variable va en `false`: con ella
en `true`, cualquiera se desbloquea la app mandando un recibo inventado.

## Cuando algo no arranca

**`port is already allocated`** — algo ya tiene ese puerto. Primero, quién:

```bash
lsof -nP -iTCP:5001 -sTCP:LISTEN
```

Si `lsof` responde `com.docke...`, **el puerto lo tiene otro contenedor**, no
un proceso suelto. Ojo con la trampa: `docker compose down` desde aquí solo
para los contenedores de ESTE proyecto. Si quien ocupa el puerto es otro
—iBet, por ejemplo—, no se entera. Para ver quién es de verdad:

```bash
docker ps --format '{{.Names}}\t{{.Ports}}'
```

Las causas, por frecuencia:

1. **Otro proyecto tuyo.** iBet publica su API en el 5000; por eso AztecApp usa
   el 5001. Si el choque es en otro puerto, muévelo en vez de parar el otro
   proyecto:

   ```bash
   API_PORT=5002 docker compose up
   flutter run --dart-define=API_BASE=http://localhost:5002
   ```

2. **AirPlay Receiver**, que en macOS se queda el 5000 y el 7000 desde
   Monterey. Aparece como `ControlCenter`. Para liberarlo: Ajustes del Sistema
   → General → AirDrop y Handoff → apagar "Receptor de AirPlay".

3. **Un `python run.py` tuyo todavía vivo**. `lsof` lo señala como `Python`; se
   cierra con `kill <PID>`.

4. **Un contenedor de este proyecto mal parado**: `docker compose down`.

El mock y la base también se pueden mover: `MOCK_PORT=4011` y `DB_PORT=5433`.

**La API se reinicia en bucle** — `docker compose logs api`. Casi siempre es
que las migraciones fallaron: el mensaje de Alembic sale ahí entero.

**Cambiaste un modelo y la API no lo ve** — falta la migración:

```bash
docker compose exec api flask db migrate -m "lo que cambiaste"
docker compose exec api flask db upgrade
```

**Quieres empezar de cero** — `docker compose down -v && docker compose up`.

## Correr los tests

```bash
docker compose exec api python -m pytest -q
```

Van contra una base de test aparte que se crea sola; no tocan tus datos de
desarrollo.

Los tres verificadores del front no necesitan Docker ni Dart, desde
`AztecAppFrontend/`:

```bash
python3 tools/check_dart_contract.py
python3 tools/check_against_live.py http://localhost:5001
python3 tools/sanity_dart.py
```
