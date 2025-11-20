# Open Positions Backend (FastAPI + SQLAlchemy)

A high-performance REST API for managing trading positions, orders, and broker configurations using async SQLAlchemy and FastAPI.

## Features

- 🚀 **FastAPI** - Modern async Python web framework
- 🔐 **JWT Authentication** - Secure token-based auth with `PyJWT`
- 🔄 **Async SQLAlchemy** - Non-blocking database operations with `sqlalchemy[asyncio]`
- 📊 **Complete REST API** - Endpoints for positions, orders, trades, and aliases
- ⚡ **AsyncPG** - High-performance async PostgreSQL driver
- 🛡️ **CORS Support** - Pre-configured for local frontend development
- 📝 **Auto API Docs** - Built-in Swagger UI and ReDoc

## Prerequisites

- **Python 3.11+**
- **PostgreSQL** (or supported async database)
- **pip** (Python package manager)

## Installation

### 1. Create and Activate Virtual Environment

**PowerShell:**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If you get an execution policy error:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Windows Command Prompt:**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `sqlalchemy[asyncio]` - Async ORM
- `asyncpg` - PostgreSQL driver
- `pydantic` - Data validation
- `pyjwt` - JWT authentication
- `python-dotenv` - Environment variable management


2. cd backend
3. uvicorn main:app --reload --host 0.0.0.0 --port 8000

### 3. Configure Environment Variables

Create a `.env` file in the `backend` folder:

```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/open_positions
JWT_SECRET=your-super-secret-key-change-this
JWT_ALGORITHM=HS256
```

### 4. Initialize Database

```bash
# Create the database tables
python -c "
import asyncio
from database import engine, Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init_db())
"
```

## Development

### Start the Backend Server

From the `backend` folder with venv activated:

```bash
uvicorn main:app --reload
```

The `--reload` flag auto-restarts the server when code changes.

**Server runs at:** `http://localhost:8000`

### API Documentation

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Project Structure

```
backend/
├── main.py              # FastAPI app & endpoints
├── models.py            # SQLAlchemy ORM models
├── database.py          # Database configuration & session management
├── auth.py              # JWT authentication logic
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (create this)
└── README.md            # This file
```

### Key Files

#### `main.py`
Contains the FastAPI application and all route endpoints:
- `GET /` - API info
- `GET /health` - Health check
- `GET /positions_json` - List open positions
- `GET /aliases` - List trader aliases
- `GET /internal_order` - List internal orders
- `GET /broker_order` - List broker orders
- `GET /trades` - List trades
- `POST /api/login` - User authentication

#### `models.py`
Defines SQLAlchemy ORM models:
- `Order` - Trading orders
- `BrokerConfig` - Broker configurations
- `InternalOrder` - Internal order tracking
- `BrokerOrder` - Broker-side orders
- `Trade` - Completed trades

#### `database.py`
Database configuration:
- AsyncSession setup
- Database engine initialization
- Session dependency for FastAPI

#### `auth.py`
Authentication utilities:
- JWT token creation
- Token verification
- Login request validation

## API Endpoints

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API info & available endpoints |
| GET | `/health` | Health check |
| POST | `/api/login` | Login with email/password |

### Protected Endpoints (require token)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/positions_json` | List open positions (paginated) |
| GET | `/aliases` | List all trader aliases |
| GET | `/internal_order` | List internal orders (paginated) |
| GET | `/broker_order` | List broker orders (paginated) |
| GET | `/trades` | List trades (paginated) |

### Query Parameters

All list endpoints support:
- `page` (default: 1) - Page number for pagination
- `limit` (default: 20) - Records per page
- `broker`, `client_id`, `ticker`, `product`, `action`, `account` - Filter parameters

Example:
```
GET /positions_json?page=1&limit=50&ticker=AAPL
```

## Authentication

### Login Flow

1. **POST** to `/api/login` with credentials:
```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

2. **Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "email": "user@example.com",
    "name": "User Name"
  }
}
```

3. **Include token** in subsequent requests:
```
Authorization: Bearer <access_token>
```

## Database Setup

### PostgreSQL (Recommended)

Install PostgreSQL and create a database:

```sql
CREATE DATABASE open_positions;
CREATE USER openpos WITH PASSWORD 'your-password';
ALTER ROLE openpos SET client_encoding TO 'utf8';
ALTER ROLE openpos SET default_transaction_isolation TO 'read committed';
ALTER ROLE openpos SET default_transaction_deferrable TO on;
ALTER ROLE openpos SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE open_positions TO openpos;
```

Update `.env`:
```env
DATABASE_URL=postgresql+asyncpg://openpos:your-password@localhost:5432/open_positions
```

### Other Databases

Async drivers available for:
- **MySQL:** `aiomysql`
- **SQLite:** `aiosqlite`

## Development Tips

### Hot Reload
The `--reload` flag watches all `.py` files and restarts the server automatically:
```bash
uvicorn main:app --reload
```

### Debug Mode
Enable debug logging:
```bash
uvicorn main:app --reload --log-level debug
```

### Different Host/Port
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8001
```

### Test the API
Use the built-in Swagger UI at `http://localhost:8000/docs` to test endpoints interactively.

## Troubleshooting

### ImportError: No module named 'sqlalchemy.ext.asyncio'
Make sure you installed SQLAlchemy correctly:
```bash
pip install "sqlalchemy[asyncio]"
```

### Database Connection Error
- Check PostgreSQL is running
- Verify `DATABASE_URL` in `.env`
- Ensure database and user exist
- Test connection: `psql -U openpos -h localhost -d open_positions`

### Port Already in Use
Run on a different port:
```bash
uvicorn main:app --reload --port 8001
```

### CORS Issues
CORS is pre-configured for local development on:
- `http://localhost:5173` (Vite default)
- `http://127.0.0.1:5173`

For other origins, update `main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Production Deployment

### Environment Variables
Set in your production environment:
```env
DATABASE_URL=postgresql+asyncpg://prod-user:prod-password@prod-host:5432/open_positions
JWT_SECRET=strong-random-secret-key
JWT_ALGORITHM=HS256
```

### Run with Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

### Docker
Example `Dockerfile`:
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0"]
```

## Support

For issues or questions:
1. Check the API docs at `/docs`
2. Review logs in the terminal
3. Check database connection
4. Verify environment variables are set

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Async Guide](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [JWT.io](https://jwt.io/)
