# Basira LMS

Basira is a learning management system with a Next.js web app and a FastAPI API backed by PostgreSQL and pgvector.

## Features

- Student and teacher accounts, with a separately bootstrapped administrator.
- Public registration is limited to student and teacher roles; administrator accounts are bootstrapped separately.
- Course, module, lesson, assignment, quiz, calendar, and inbox workflows.
- Assignment submissions and teacher grading.
- Student-only course assistant using Cohere and pgvector retrieval.
- YouTube transcript retrieval with optional OpenAI transcription fallback.
- Email verification and password recovery through backend SMTP.

## Architecture

```text
frontend/  Next.js App Router application
backend/   FastAPI API, SQLAlchemy models, Alembic migrations, and AI services
PostgreSQL PostgreSQL database with the pgvector extension
```

The browser calls the FastAPI API. The API enforces authentication and role permissions and accesses PostgreSQL. The AI assistant uses Cohere and retrieved course documents; OpenAI transcription is optional.

## Requirements

- Python 3.10 or newer
- Node.js 20.9 or newer
- PostgreSQL with the pgvector extension
- SMTP credentials for verification and password-reset email

## Backend setup

From PowerShell:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Set the values in `backend/.env`:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection URL using the `postgresql+psycopg` driver |
| `JWT_SECRET` | Random secret of at least 32 bytes |
| `JWT_ALGORITHM` | Must be `HS256` |
| `ADMIN_EMAIL` | The single administrator account's email |
| `ADMIN_INITIAL_PASSWORD` | Initial administrator password, at least 10 characters |
| `FRONTEND_URL` | Frontend origin used in email links |
| `FRONTEND_ORIGINS` | JSON array of allowed frontend origins |
| `SMTP_HOST`, `SMTP_PORT` | SMTP server settings; Gmail commonly uses `smtp.gmail.com:587` |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | SMTP account and app password |
| `SMTP_FROM_EMAIL`, `SMTP_FROM_NAME` | Sender displayed in auth emails |
| `COHERE_API_KEY` | Optional; enables the course assistant |
| `OPENAI_API_KEY` | Optional; enables transcription fallback |

Generate a JWT secret locally:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

For Gmail, use an App Password rather than your regular account password. Do not commit `.env` or paste secret values into source files.

Apply migrations and create the administrator:

```powershell
alembic upgrade head
python bootstrap_admin.py
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

The API health endpoint is `http://localhost:8000/api/v1/health`; FastAPI's interactive docs are available at `http://localhost:8000/docs`.

Existing accounts without a local password must use password recovery to set one. SMTP must be configured for registration verification and password recovery.

## Frontend setup

In another PowerShell window:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env.local
npm run dev
```

Set `NEXT_PUBLIC_API_URL` in `frontend/.env.local` to the backend API URL. The Supabase URL and anon key in that example are only used by the legacy `/auth/confirm` page; never put a Supabase service-role key or other private key in a `NEXT_PUBLIC_` variable.

Open `http://localhost:3000`.

## Checks

```powershell
# Backend, from backend/
python -m pip install -r requirements-dev.txt
pytest -q

# Frontend, from frontend/
npm run lint
npm run build
```

## Security notes

- Passwords use Argon2id. Access tokens are short-lived JWTs; refresh tokens are rotated and stored in an HttpOnly cookie.
- Email action tokens are stored as SHA-256 hashes and expire.
- Student, teacher, and administrator permissions are checked by the backend, not only by the UI. The AI endpoint is restricted to students and rate-limited server-side.
- Configure exact production CORS origins, HTTPS, and secrets through the deployment environment.
- Authentication rate limits are process-local. Deployments with multiple API workers should use a shared rate-limit store.
- Keep `.env`, `.env.local`, database credentials, SMTP credentials, and private API keys out of GitHub.
