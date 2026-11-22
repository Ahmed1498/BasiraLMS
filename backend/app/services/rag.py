# import asyncio
# import logging
# from uuid import UUID

# import cohere
# from app.core.config import settings
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from sqlalchemy.exc import SQLAlchemyError
# from fastapi import HTTPException
# from app.models.models import CourseDocument

# logger = logging.getLogger(__name__)
# co = cohere.Client(api_key=settings.COHERE_API_KEY) if settings.COHERE_API_KEY else None

# async def generate_embedding(text: str) -> list[float]:
#     if not co:
#         raise HTTPException(status_code=503, detail="Course search is not configured on this server")

#     try:
#         response = await asyncio.to_thread(
#             co.embed,
#             texts=[text],
#             model="embed-multilingual-v3.0",
#             input_type="search_query",
#             output_dimension=1536,
#         )
#         return response.embeddings[0]
#     except Exception as exc:
#         logger.exception("Cohere embedding request failed")
#         raise HTTPException(status_code=502, detail="Course search could not process this request") from exc

# async def retrieve_rag_context(db: AsyncSession, course_id: UUID | None, query: str) -> str:
#     query_embedding = await generate_embedding(query)

#     try:
#         if course_id:
#             # Query course-specific documents
#             result = await db.execute(
#                 select(CourseDocument)
#                 .where(CourseDocument.course_id == course_id)
#                 .order_by(CourseDocument.embedding.cosine_distance(query_embedding))
#                 .limit(3)
#             )
#         else:
#             # Query all documents across courses
#             result = await db.execute(
#                 select(CourseDocument)
#                 .order_by(CourseDocument.embedding.cosine_distance(query_embedding))
#                 .limit(3)
#             )

#         documents = result.scalars().all()
#         if not documents:
#             return ""

#         context_chunks = [doc.chunk_text for doc in documents]
#         return "\n\n---\n\n".join(context_chunks)
#     except SQLAlchemyError as exc:
#         logger.exception("Course document retrieval failed")
#         raise HTTPException(status_code=503, detail="Course materials are temporarily unavailable") from exc





import asyncio
import logging
from uuid import UUID

import cohere
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from fastapi import HTTPException
from app.models.models import CourseDocument, VideoTranscript, VideoTranscriptChunk

logger = logging.getLogger(__name__)

EMBED_MODEL = "embed-v4.0"
EMBED_DIMENSION = 1536  # لازم يطابق Vector(1536) في الداتابيز
CHAT_MODEL = "command-a-03-2025"  # بدل "command" اللي اتشالت

co = cohere.ClientV2(api_key=settings.COHERE_API_KEY) if settings.COHERE_API_KEY else None


async def generate_embeddings(texts: list[str], input_type: str) -> list[list[float]]:
    if not co:
        raise HTTPException(status_code=503, detail="Course search is not configured on this server")
    if not texts:
        return []

    try:
        embeddings: list[list[float]] = []
        for start in range(0, len(texts), 96):
            response = await asyncio.to_thread(
                co.embed,
                texts=texts[start : start + 96],
                model=EMBED_MODEL,
                input_type=input_type,
                embedding_types=["float"],
                output_dimension=EMBED_DIMENSION,
            )
            embeddings.extend(list(embedding) for embedding in response.embeddings.float_)
        return embeddings
    except Exception as exc:
        logger.exception("Cohere embedding request failed; exception_type=%s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Course search could not process this request") from exc


async def generate_embedding(text: str, input_type: str = "search_query") -> list[float]:
    embeddings = await generate_embeddings([text], input_type)
    return embeddings[0]


def chunk_transcript(text: str, chunk_size: int = 800) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            boundary = max(
                text.rfind(" ", start + 500, end),
                text.rfind("\n", start + 500, end),
                text.rfind(". ", start + 500, end),
                text.rfind("؟", start + 500, end),
            )
            if boundary > start:
                end = boundary + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start = end
    return chunks


async def index_video_transcript(
    db: AsyncSession,
    transcript: VideoTranscript,
) -> None:
    count_result = await db.execute(
        select(func.count(VideoTranscriptChunk.id)).where(
            VideoTranscriptChunk.transcript_id == transcript.id
        )
    )
    if count_result.scalar_one() > 0:
        return

    chunks = chunk_transcript(transcript.transcript)
    embeddings = await generate_embeddings(chunks, input_type="search_document")
    db.add_all(
        VideoTranscriptChunk(
            transcript_id=transcript.id,
            chunk_text=chunk,
            embedding=embedding,
        )
        for chunk, embedding in zip(chunks, embeddings)
    )
    await db.flush()


async def retrieve_video_transcript_context(
    db: AsyncSession,
    transcript_id: UUID,
    query: str,
) -> str:
    count_result = await db.execute(
        select(func.count(VideoTranscriptChunk.id)).where(
            VideoTranscriptChunk.transcript_id == transcript_id
        )
    )
    if count_result.scalar_one() == 0:
        return ""

    query_embedding = await generate_embedding(query, input_type="search_query")
    try:
        result = await db.execute(
            select(VideoTranscriptChunk)
            .where(VideoTranscriptChunk.transcript_id == transcript_id)
            .order_by(VideoTranscriptChunk.embedding.cosine_distance(query_embedding))
            .limit(4)
        )
        chunks = result.scalars().all()
        return "\n\n---\n\n".join(chunk.chunk_text for chunk in chunks)
    except SQLAlchemyError as exc:
        logger.exception("Video transcript retrieval failed")
        raise HTTPException(status_code=503, detail="Video transcript search is temporarily unavailable") from exc


async def retrieve_rag_context(db: AsyncSession, course_id: UUID | None, query: str) -> str:
    if course_id is None:
        return ""

    query_embedding = await generate_embedding(query, input_type="search_query")

    try:
        stmt = select(CourseDocument)
        stmt = stmt.where(CourseDocument.course_id == course_id)

        result = await db.execute(
            stmt.order_by(CourseDocument.embedding.cosine_distance(query_embedding)).limit(3)
        )

        documents = result.scalars().all()
        if not documents:
            return ""

        return "\n\n---\n\n".join(doc.chunk_text for doc in documents)
    except SQLAlchemyError as exc:
        logger.exception("Course document retrieval failed")
        raise HTTPException(status_code=503, detail="Course materials are temporarily unavailable") from exc


async def generate_answer(question: str, context: str = "", history: list[dict] | None = None) -> str:
    """Generate the assistant's reply with Cohere chat (v2 API)."""
    if not co:
        raise HTTPException(status_code=503, detail="AI assistant is not configured on this server")

    system_prompt = (
        "You are Basira AI Agent, a helpful assistant for an online learning platform. "
        "Answer the student's question using the course material below when it is relevant. "
        "If the material does not contain the answer, say so honestly. "
        "Reply in the same language the student writes in."
    )
    if context:
        system_prompt += f"\n\nCourse material:\n{context}"

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        # كل عنصر: {"role": "user" | "assistant", "content": "..."}
        messages.extend(history)
    messages.append({"role": "user", "content": question})

    try:
        response = await asyncio.to_thread(
            co.chat,
            model=CHAT_MODEL,
            messages=messages,
        )
        return response.message.content[0].text
    except Exception as exc:
        logger.exception("Cohere chat request failed")
        raise HTTPException(status_code=502, detail="The AI provider could not answer this request") from exc