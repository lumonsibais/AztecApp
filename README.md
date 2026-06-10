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
GET    /api/payments/history     - Historial de pagos
POST   /api/payments/create      - Crear pago
```

### Historical
```
GET    /api/historical/content   - Contenido histórico
GET    /api/historical/timelines - Timelines
GET    /api/historical/lake-view - Datos del lago
```

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