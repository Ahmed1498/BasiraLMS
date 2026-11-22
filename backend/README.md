# Basira LMS API

FastAPI services backed by PostgreSQL/pgvector and Supabase Auth.

## Configure

1. Use PostgreSQL with the `vector` extension available.
2. Copy `.env.example` to `.env` and set:
   - `DATABASE_URL` using the `postgresql+psycopg://` driver.
   - `SUPABASE_URL` and `SUPABASE_JWT_SECRET` from the Supabase project.
   - `SUPABASE_SERVICE_ROLE_KEY` if administrators should send invitations. This key is server-only and must never be added to the frontend.
   - `COHERE_API_KEY` to enable the AI assistant.
   - `OPENAI_API_KEY` to enable Whisper audio transcription when a YouTube video has no usable captions or YouTube blocks caption retrieval. The downloaded audio is sent to OpenAI's Whisper API; leave unset to disable this fallback.
   - `FRONTEND_ORIGINS` to the exact frontend origins allowed to call the API. The defaults permit both `http://localhost:3000` and `http://127.0.0.1:3000` for local development.
3. Install dependencies and initialize the schema from this folder:

   ```powershell
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   alembic upgrade head
   python seed.py
   ```

   If there is no virtual environment yet, create one with `py -m venv .venv` before activating it.
4. Start the API:

   ```powershell
   uvicorn app.main:app --reload
   ```

   Health check: `http://localhost:8000/api/v1/health`. Interactive API docs: `http://localhost:8000/docs`.

## First administrator

Create and confirm a Supabase Auth user for `ADMIN_EMAIL` (default: `ahm145ali145@gmail.com`) in the Supabase dashboard. Public signup is blocked for this reserved address. Set `BOOTSTRAP_ADMIN_ID` to that user's UUID and `BOOTSTRAP_ADMIN_EMAIL` to the same configured `ADMIN_EMAIL` in the backend environment, then run:

```powershell
python bootstrap_admin.py
```

The script promotes only the matching Supabase account profile in the application database. Remove those one-time variables after bootstrapping. Then sign in through the frontend with the Supabase email and password; Supabase validates the password and the application database supplies the administrator role. Admin passwords are managed by Supabase Auth and must not be stored in source code.

The signup confirmation link completes at `/auth/confirm` and routes the signed-in user to their role dashboard. Password recovery sends a link to `/reset-password`; after a successful password update, the user is routed to their role dashboard.

## API behavior

- Protected endpoints require a valid Supabase access token.
- Supabase access tokens are validated using the configured HS256 secret or Supabase's published JWKS for ES256/RS256 signing keys.
- The first authenticated request creates a student profile; roles are stored in the application database.
- Teachers can manage only their own courses. Students must enroll before submitting work, completing lessons, or taking quizzes.
- Quiz answers are checked and scored on the server. Correct answers are never returned by the student-facing quiz endpoint.
- If an external service is missing or unavailable, the API returns a non-success status and a useful error rather than fake success data.

The local rate limiter for AI requests is in-memory and is intended for a single-instance MVP deployment.
