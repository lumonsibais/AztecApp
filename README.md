# Aztec Explorer 🏛️

Aplicación móvil para exploradores independientes que desean descubrir sitios de la cultura azteca en la CDMX con contexto histórico y herramientas prácticas de navegación.

## 📱 Propósito

Ayudar a personas viajeras a:
- **Descubrir** sitios arqueológicos y culturales
- **Entender** su valor histórico
- **Explorar** con autonomía sin necesidad de tours guiados

## 🏛️ Propuesta de Valor

- 📍 Mapa interactivo con descubrimiento de sitios cercanos
- 🗺️ Vista histórica del lago de Tenochtitlan
- 🚶 Tours autogestionados con rutas claras
- 📚 Contenido histórico verificado y multimedia
- 💰 Modelo freemium con acceso premium

## 📁 Estructura del Proyecto

```
AztecApp/
├── app/                          # Backend (Flask Monolito Modular)
│   ├── places/                  # Módulo: Sitios y descubrimiento
│   ├── tours/                   # Módulo: Tours autogestionados
│   ├── users/                   # Módulo: Usuarios y auth
│   ├── payments/                # Módulo: Pagos y suscripciones
│   ├── historical/              # Módulo: Contenido histórico
│   ├── shared/                  # Utilidades compartidas
│   └── middleware/              # Autenticación
├── run.py                       # Entry point
├── manage.py                    # CLI utilities
├── requirements.txt             # Python dependencies
└── BACKEND_README.md           # Documentación del backend
```

## 🚀 Quick Start - Backend

### Requisitos
- Python 3.9+
- PostgreSQL (recomendado) o SQLite
- Pip/Conda

### Instalación

```bash
# 1. Clone repository
git clone <repo>
cd AztecApp

# 2. Virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Setup environment
cp .env.example .env
# Edit .env with your configuration

# 5. Initialize database
python manage.py init

# 6. Run server
python run.py
```

Server estará disponible en: `http://localhost:5000`

## 📚 Documentación

- [BACKEND_README.md](./BACKEND_README.md) - Documentación completa del backend
- [BACKEND_SETUP.md](./BACKEND_SETUP.md) - Setup y configuración detallada

## 🔌 API Endpoints

### Places (Sitios)
```
GET    /api/places/nearby        - Sitios cercanos
GET    /api/places/              - Todos los sitios
GET    /api/places/<id>          - Detalles del sitio
GET    /api/places/recommended   - Recomendados
```

### Tours
```
GET    /api/tours/free           - Tours gratis (máx 3)
GET    /api/tours/               - Todos los tours
GET    /api/tours/<id>           - Detalles
POST   /api/tours/<id>/start     - Iniciar tour
POST   /api/tours/<id>/complete  - Completar tour
```

### Users
```
POST   /api/users/register       - Registrar
POST   /api/users/login          - Login
GET    /api/users/profile        - Perfil del usuario
```

### Payments
```
GET    /api/payments/access            - ¿Tiene esta cuenta el desbloqueo?
GET    /api/payments/purchases         - Historial de compras
POST   /api/payments/checkout          - Abrir una compra
POST   /api/payments/confirm           - Verificar el recibo y conceder el acceso
POST   /api/payments/restore           - Restore Purchases
POST   /api/payments/webhooks/apple    - Avisos de la App Store (los llama Apple)
POST   /api/payments/webhooks/google   - Avisos de Google Play (los llama Pub/Sub)
```

### Historical
```
GET    /api/historical/content   - Contenido histórico
GET    /api/historical/timelines - Timelines
GET    /api/historical/lake-view - Datos del lago
```

## 💳 Cobro desde las tiendas

El desbloqueo se compra **dentro de la app**, con In-App Purchase de Apple y
Play Billing de Google. El servidor no cobra: cobra la tienda, y aquí solo se
comprueba contra ella que el recibo que presenta la app es cierto, es nuestro y
sigue vivo. Lo que manda el cliente no desbloquea nada por sí mismo.

### Lo que hay que dar de alta (una vez, y no lo puede hacer el código)

**App Store Connect**

1. Un producto **no consumible** con su identificador → `APPLE_PRODUCT_ID`.
2. Una clave de API de In-App Purchase (Users and Access → Integrations). Se
   descarga **una sola vez**: el `.p8` → `APPLE_PRIVATE_KEY`, y con él el
   *Key ID* → `APPLE_KEY_ID` y el *Issuer ID* → `APPLE_ISSUER_ID`.
3. El bundle id de la app → `APPLE_BUNDLE_ID`.
4. La URL de notificaciones V2 apuntando a `/api/payments/webhooks/apple`.

**Play Console + Google Cloud**

1. Un producto **gestionado** (one-time) con su id → `GOOGLE_PRODUCT_ID`.
2. Una cuenta de servicio con acceso a la app y permiso para ver datos
   financieros; su JSON → `GOOGLE_SERVICE_ACCOUNT_JSON`.
3. El nombre del paquete → `GOOGLE_PACKAGE_NAME`.
4. Un tema de Pub/Sub para las *real-time developer notifications*, con entrega
   push a `/api/payments/webhooks/google`.

Sin estas credenciales, `/payments/confirm` responde **402** diciendo que el
cobro no está configurado. Es a propósito: un servidor a medio configurar niega
el acceso, no lo regala.

### Lo que tiene que hacer la app

- Mandar el **id de usuario** al iniciar la compra: `appAccountToken` en
  StoreKit 2, `obfuscatedExternalAccountId` en Play Billing. La tienda lo
  devuelve intacto y el servidor lo comprueba; es la única defensa contra el
  reenvío de recibos ajenos que no se puede falsificar desde el cliente.
- Mandar a `/payments/confirm` el **transactionId** (Apple) o el
  **purchaseToken** (Google) en `externalId`.
- Enseñar el precio que da la tienda, no el de `/payments/access`: ese es solo
  una referencia. El que paga el comprador lo fija el escalón de precio elegido
  en cada consola, en la moneda de su país.
- Tener un botón **Restore Purchases** contra `/payments/restore`. Apple rechaza
  en revisión toda app con producto no consumible que no lo ofrezca.

### Lo que tiene que correr en el servidor

```bash
flask payments acusar-pendientes     # una vez al día, en cron
```

Google **reembolsa automáticamente** toda compra que no se acuse en 3 días. El
acuse normal se hace justo después de conceder el acceso, pero si esa llamada
falla nadie se entera: al usuario ya se le respondió que todo fue bien. Este
comando recoge las que se quedaron atrás. Sin él, el fallo se ve en el informe
de ingresos y no antes.

### Altas a mano

```bash
flask payments grant alguien@ejemplo.com --motivo "prueba de prensa"
```

Para cortesías, pruebas y soporte. Está en la consola y no en la API por lo
mismo que el rol de administrador: un acceso que se concede por la API es un
acceso que alguien va a intentar concederse.

### Los webhooks no llevan autenticación, y está bien

Los llaman Apple y Pub/Sub, así que no pueden llevarla. Lo que los hace seguros
es que **el contenido de la notificación no decide nada**: de él solo se saca el
identificador de la compra, y la verdad se pide después a la tienda por una
conexión autenticada nuestra. Una notificación falsificada no concede ni revoca
nada; lo peor que consigue quien la invente es que le preguntemos a Apple por una
compra. `STORE_WEBHOOK_SECRET` añade un secreto en la URL para evitar hasta eso,
pero es un extra, no lo que sostiene el diseño.

## 🏗️ Arquitectura

### Patrón: Monolito Modular en Capas

Cada módulo implementa:
1. **Models** - Esquemas de BD
2. **Repositories** - Acceso a datos
3. **Services** - Lógica de negocio
4. **Controllers** - Endpoints HTTP

```
HTTP Request
    ↓
Controller → Service → Repository → Database
    ↓
HTTP Response
```

## 🔐 Autenticación

Usa JWT tokens para endpoints protegidos:

```bash
# Login
POST /api/users/login
{
  "email": "user@example.com",
  "password": "password123"
}

# Response
{
  "success": true,
  "data": {
    "accessToken": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "user": {...}
  }
}

# Usar token
Authorization: Bearer <token>
```

## 📊 Base de Datos

**Tablas principales:**
- `users` - Usuarios y suscripciones
- `places` - Sitios arqueológicos
- `tours` - Tours autogestionados
- `tour_progress` - Progreso del usuario
- `payments` - Historial de transacciones
- `subscriptions` - Suscripciones activas
- `historical_content` - Contenido histórico

## 🛠️ Desarrollo

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app
```

### Database Migrations
```bash
# Create migration
flask db migrate -m "Description"

# Apply
flask db upgrade

# Rollback
flask db downgrade
```

## 🤝 User Stories (MVP)

### HU 1: Descubrimiento de Sitios
```
As Tim (explorer independiente)
I want to find Aztec sites in the city
So I can visit them
```

### HU 2: Vista Histórica del Lago
```
As Tim
I want to understand what part of Tenochtitlan I'm in
So I can feel like an explorer
```

### HU 3: Tours Autogestionados
```
As Tim
I want to get suggested visits
So I can quickly follow a plan
```

## 🔄 Flujo de Negocio (MVP)

```
1. Usuario abre app
2. Solicita acceso a ubicación
3. Ve sitios cercanos en mapa
4. Elige sitio para explorar
5. Lee contenido histórico
6. (Optional) Inicia tour
7. Completa tour y deja rating
8. (Premium) Unlock contenido pagado
```

## 💰 Modelo de Negocio

- **Free tier**: 3 tours + contenido básico
- **Premium**: $9.99/mes - Tours ilimitados + contenido completo
- **VIP**: $19.99/mes - Premium + contenido exclusivo

## 🚨 Next Steps

1. ✅ Estructura base del backend
2. ⏳ Implementar seed de datos (sitios reales)
3. ⏳ Integración con Stripe
4. ⏳ Mobile app (Flutter/React Native)
5. ⏳ ML recommendations
6. ⏳ Real-time notifications

## 📞 Contacto y Soporte

- 📧 Email: support@aztecexplorer.com
- 💬 Issues: GitHub Issues
- 📚 Docs: [BACKEND_README.md](./BACKEND_README.md)

## 📄 Licencia

TBD

---

**Versión**: 0.1.0 (MVP)  
**Estado**: En desarrollo 🚧  
**Última actualización**: Junio 2026