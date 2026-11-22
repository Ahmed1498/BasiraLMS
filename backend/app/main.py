import asyncio
import logging
from uuid import UUID

import cohere
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import enforce_ai_rate_limit
from app.api import admin, auth, courses, assignments, quizzes, users, calendar, messages
from app.models.models import VideoTranscript
from app.services.rag import (
    index_video_transcript,
    retrieve_rag_context,
    retrieve_video_transcript_context,
)
from app.services.transcript import (
    extract_video_url,
    extract_youtube_id,
    get_video_transcript,
    transcribe_video_with_whisper,
)
from app.schemas.api import AIChatRequest

logger = logging.getLogger(__name__)

CHAT_MODEL = "command-a-03-2025"  # بدل "command" اللي اتشالت

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Basira LMS Backend API with Supabase Auth, RBAC, and Cohere RAG AI Integration"
)

# Initialize Cohere client (v2) if API key is provided
co = cohere.ClientV2(api_key=settings.COHERE_API_KEY) if settings.COHERE_API_KEY else None


def parse_course_id(raw_course_id: str | None) -> UUID | None:
    if not raw_course_id:
        return None
    try:
        return UUID(raw_course_id)
    except (TypeError, ValueError):
        logger.warning("Ignoring invalid courseId in AI page context")
        return None


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(courses.router)
app.include_router(assignments.router)
app.include_router(quizzes.router)
app.include_router(admin.router)
app.include_router(users.router)
app.include_router(auth.router)
app.include_router(calendar.router)
app.include_router(messages.router)


@app.get("/")
async def root():
    return {"message": "Welcome to Basira LMS API", "status": "active"}


@app.get("/api/v1/health")
async def health_check():
    return {"status": "healthy"}


# Advanced RAG-Powered AI Chat Endpoint with Cohere LLM & pgvector Retrieval
@app.post("/api/v1/ai/chat")
async def ai_chat(
    prompt_data: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(enforce_ai_rate_limit),
):
    if co is None:
        raise HTTPException(status_code=503, detail="AI chat is not configured on this server")

    prompt = prompt_data.prompt.strip()
    page_context = prompt_data.page_context or {}
    lesson_title = page_context.get("lessonTitle") or "Current Lesson"
    lesson_body = page_context.get("contentBody") or ""
    raw_course_id = page_context.get("courseId")
    video_url = (page_context.get("videoUrl") or "").strip() or extract_video_url(prompt) or ""
    video_id = extract_youtube_id(video_url) if video_url else None

    course_id = parse_course_id(raw_course_id)
    course_context_status = (
        "available" if course_id else "invalid_course_id" if raw_course_id else "not_provided"
    )

    transcript_record = None
    transcript_length = 0
    transcript_source = None
    transcript_reason = "video_url_missing" if not video_url else None
    if video_id:
        result = await db.execute(
            select(VideoTranscript).where(VideoTranscript.video_id == video_id)
        )
        transcript_record = result.scalar_one_or_none()

        if transcript_record is None:
            captions = await get_video_transcript(video_url)
            transcript_text = captions.text
            transcript_source = captions.source
            caption_failure = captions.reason

            if not transcript_text and caption_failure in {"no_captions", "blocked", "youtube_error"}:
                whisper_result = await transcribe_video_with_whisper(video_id)
                transcript_text = whisper_result.text
                transcript_source = whisper_result.source
                if not transcript_text:
                    transcript_reason = caption_failure
                    if captions.exception_type:
                        transcript_reason += f" ({captions.exception_type})"
                    if whisper_result.reason:
                        transcript_reason += f"; {whisper_result.reason}"
                    if whisper_result.exception_type:
                        transcript_reason += f" ({whisper_result.exception_type})"

            if transcript_text:
                transcript_record = VideoTranscript(
                    video_id=video_id,
                    video_url=f"https://www.youtube.com/watch?v={video_id}",
                    transcript=transcript_text,
                    source=transcript_source or "captions",
                )
                db.add(transcript_record)
                await db.flush()
                transcript_reason = None
            elif transcript_reason is None:
                transcript_reason = caption_failure or "no_captions"

        if transcript_record is not None:
            transcript_length = len(transcript_record.transcript)
            transcript_source = transcript_record.source
            try:
                await index_video_transcript(db, transcript_record)
            except HTTPException as exc:
                logger.exception(
                    "Could not index transcript for video %s; exception_type=%s",
                    video_id,
                    type(exc).__name__,
                )
                transcript_reason = "transcript_indexing_failed"
    elif video_url:
        transcript_reason = "not_youtube"

    rag_context = await retrieve_rag_context(db, course_id, prompt) if course_id else ""
    video_context = ""
    if transcript_record is not None and transcript_reason != "transcript_indexing_failed":
        video_context = await retrieve_video_transcript_context(
            db,
            transcript_record.id,
            prompt,
        )

    logger.warning(
        "AI chat video diagnostics | lessonTitle=%r | contentBody_len=%d | courseId=%r | video_url_present=%s | video_id=%r | transcript_source=%r | transcript_reason=%r | transcript_len=%d | video_rag_len=%d | rag_len=%d",
        lesson_title,
        len(lesson_body),
        raw_course_id,
        bool(video_url),
        video_id,
        transcript_source,
        transcript_reason,
        transcript_length,
        len(video_context),
        len(rag_context),
    )

    combined_context = (
        f"Lesson Title: {lesson_title}\n\n"
        f"Direct Lesson Content:\n{lesson_body}\n\n"
        f"Video URL: {video_url or 'none'}\n"
        f"Video transcript source: {transcript_source or 'none'}\n"
        f"Video transcript status: {'available' if video_context else 'unavailable'}\n"
        f"Video transcript reason: {transcript_reason or 'none'}\n\n"
        f"Course document retrieval status: {course_context_status}\n\n"
        f"Relevant video transcript excerpts:\n{video_context or 'none retrieved'}\n\n"
        f"Retrieved Course Documents:\n{rag_context}"
    )
    system_prompt = (
        "You are Basira AI Learning Assistant, a friendly general-purpose tutor. "
        "Answer ordinary questions normally using your knowledge; missing course or video context must never block an answer. "
        "When asked to summarize this page or lesson, summarize the Direct Lesson Content if it is present. "
        "When asked about a video, use Relevant video transcript excerpts if present. "
        "Only if the student specifically asks about video content and no excerpts were retrieved, explain the supplied transcript reason honestly instead of guessing. "
        "If a video link is needed but none was provided, ask for it only for that video-specific question. "
        "Use course documents when available, and distinguish them from general guidance. "
        "Reply in the same language the student writes in.\n\n"
        f"--- COURSE CONTEXT ---\n{combined_context}\n----------------------"
    )

    try:
        response = await asyncio.to_thread(
            co.chat,
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as exc:
        logger.exception("Cohere chat request failed")
        raise HTTPException(status_code=502, detail="The AI provider could not answer this request") from exc

    content = response.message.content if response.message else None
    answer = content[0].text if content else ""
    if not answer:
        raise HTTPException(status_code=502, detail="The AI provider returned an empty response")

    return {
        "response": answer,
        "rate_limit_status": "passed",
    }