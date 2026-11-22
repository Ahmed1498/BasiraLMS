# Basira LMS

Basira is a course platform with Supabase authentication, a FastAPI/PostgreSQL backend, student learning progress, assignment submissions and grading, quizzes, course management, administration, and an optional Cohere-powered course assistant.

## Run locally

1. Configure and start the backend using [backend/README.md](../backend/README.md).
2. Copy `.env.example` to `.env.local` and set the Supabase project URL and public anon key. Keep service-role keys and database credentials out of the frontend environment.
3. Install and start the frontend from this folder:

   ```powershell
   npm ci
   npm run dev
   ```

4. Open `http://localhost:3000`, create a student account, and confirm the email if Supabase email confirmation is enabled.

Add `http://localhost:3000/auth/confirm` and `http://localhost:3000/reset-password` to the Supabase Auth redirect URL allowlist. Configure SMTP in Supabase Auth if confirmation and recovery emails are not being delivered.

## Authentication and roles

- Public self-registration creates student accounts only.
- Administrators invite students and teachers. Invitations require `SUPABASE_SERVICE_ROLE_KEY` on the backend.
- The backend stores account roles and checks them against the authenticated user profile; it does not trust role values supplied in editable user metadata.
- For the first administrator, create/confirm the account in Supabase, then follow the one-time bootstrap instructions in [backend/README.md](../backend/README.md).

## Implemented workflows

- Students browse and enroll in courses, open modules and lessons, mark lessons complete, submit assignment links or text, and take quizzes with server-calculated scores.
- Teachers create courses, modules, lessons, assignments, and quizzes, then review and grade submissions with feedback.
- Administrators invite users, update roles and access, and view live platform counts.
- The AI assistant uses lesson context and retrieved course documents when Cohere is configured. If unavailable, the UI shows the actual service error rather than a fabricated answer.

Course file uploads and payments are not included; assignment submissions currently accept a URL or text response.
