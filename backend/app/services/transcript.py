import asyncio
import logging
import os
import re
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import parse_qs, urlparse

import httpx
from youtube_transcript_api import (
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)
from yt_dlp import YoutubeDL

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_TRANSCRIPT_CHARS = 200_000
MAX_AUDIO_BYTES = 25 * 1024 * 1024
MAX_VIDEO_DURATION_SECONDS = 2 * 60 * 60
PREFERRED_LANGUAGES = ["ar", "en"]
YOUTUBE_URL_PATTERN = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)


@dataclass(frozen=True)
class TranscriptResult:
    text: str = ""
    reason: str | None = None
    source: str | None = None
    exception_type: str | None = None


def extract_youtube_id(url: str) -> str | None:
    try:
        parsed = urlparse(url)
    except ValueError:
        return None

    host = (parsed.hostname or "").lower().removeprefix("www.")
    if host == "youtu.be":
        video_id = parsed.path.lstrip("/").split("/", 1)[0]
    elif host in {"youtube.com", "m.youtube.com", "music.youtube.com", "youtube-nocookie.com"}:
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [None])[0]
        else:
            match = re.match(r"^/(?:embed|shorts|live|v)/([\w-]{11})(?:/|$)", parsed.path)
            video_id = match.group(1) if match else None
    else:
        return None

    return video_id if video_id and re.fullmatch(r"[\w-]{11}", video_id) else None


def extract_video_url(text: str) -> str | None:
    candidates = YOUTUBE_URL_PATTERN.findall(text)
    if not candidates:
        return None
    return candidates[0].rstrip(".,;:!?)]}")


@lru_cache(maxsize=256)
def _fetch_youtube_transcript(video_id: str) -> str:
    api = YouTubeTranscriptApi()
    transcripts = api.list(video_id)
    try:
        transcript = transcripts.find_transcript(PREFERRED_LANGUAGES)
    except NoTranscriptFound:
        transcript = next(iter(transcripts), None)
        if transcript is None:
            raise
    fetched = transcript.fetch()
    return " ".join(snippet.text for snippet in fetched)


async def get_video_transcript(video_url: str) -> TranscriptResult:
    video_id = extract_youtube_id(video_url)
    if not video_id:
        return TranscriptResult(reason="not_youtube")

    try:
        text = await asyncio.to_thread(_fetch_youtube_transcript, video_id)
    except (IpBlocked, RequestBlocked) as exc:
        logger.exception(
            "YouTube captions blocked for video %s; exception_type=%s",
            video_id,
            type(exc).__name__,
        )
        return TranscriptResult(reason="blocked", exception_type=type(exc).__name__)
    except (NoTranscriptFound, TranscriptsDisabled) as exc:
        logger.warning(
            "YouTube captions unavailable for video %s; exception_type=%s",
            video_id,
            type(exc).__name__,
        )
        return TranscriptResult(reason="no_captions", exception_type=type(exc).__name__)
    except Exception as exc:
        logger.exception(
            "Could not fetch YouTube captions for video %s; exception_type=%s",
            video_id,
            type(exc).__name__,
        )
        return TranscriptResult(
            reason="youtube_error",
            exception_type=type(exc).__name__,
        )

    text = text[:MAX_TRANSCRIPT_CHARS].strip()
    if not text:
        return TranscriptResult(reason="no_captions")
    return TranscriptResult(text=text, source="captions")


def _download_and_transcribe_with_whisper(video_id: str) -> str:
    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory(prefix="basira-whisper-") as temp_dir:
        output_template = os.path.join(temp_dir, "audio.%(ext)s")
        options = {
            "format": "bestaudio/best",
            "outtmpl": output_template,
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "max_filesize": MAX_AUDIO_BYTES,
            "match_filter": (
                lambda info, *, incomplete=False:
                "Video exceeds the two-hour transcription limit"
                if info.get("duration") and info["duration"] > MAX_VIDEO_DURATION_SECONDS
                else None
            ),
        }
        with YoutubeDL(options) as downloader:
            info = downloader.extract_info(canonical_url, download=True)
            audio_path = downloader.prepare_filename(info)

        if not os.path.isfile(audio_path):
            raise RuntimeError("YouTube audio download did not produce an audio file")
        if os.path.getsize(audio_path) > MAX_AUDIO_BYTES:
            raise ValueError("Downloaded audio exceeds the 25 MB Whisper API limit")

        extension = os.path.splitext(audio_path)[1].lower()
        mime_type = {
            ".webm": "audio/webm",
            ".m4a": "audio/mp4",
            ".mp4": "audio/mp4",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
        }.get(extension, "application/octet-stream")
        with open(audio_path, "rb") as audio_file:
            response = httpx.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                data={"model": "whisper-1", "response_format": "json"},
                files={"file": (os.path.basename(audio_path), audio_file, mime_type)},
                timeout=httpx.Timeout(180.0, connect=15.0),
            )
        response.raise_for_status()
        payload = response.json()
        text = payload.get("text", "").strip()
        if not text:
            raise ValueError("Whisper returned an empty transcript")
        return text[:MAX_TRANSCRIPT_CHARS]


async def transcribe_video_with_whisper(video_id: str) -> TranscriptResult:
    if not settings.OPENAI_API_KEY:
        return TranscriptResult(reason="whisper_not_configured")

    try:
        text = await asyncio.to_thread(_download_and_transcribe_with_whisper, video_id)
    except Exception as exc:
        logger.exception(
            "Whisper fallback failed for video %s; exception_type=%s",
            video_id,
            type(exc).__name__,
        )
        return TranscriptResult(
            reason="whisper_failed",
            exception_type=type(exc).__name__,
        )

    return TranscriptResult(text=text, source="whisper")
