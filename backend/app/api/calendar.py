from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.models import Assignment, CalendarEvent, Course, Enrollment, Quiz, User

router = APIRouter(prefix="/api/v1", tags=["Calendar"])


class CalendarEventCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=5000)
    event_date: datetime
    course_id: UUID | None = None


@router.get("/calendar")
async def get_calendar(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if user.role == "student":
        course_result = await db.execute(
            select(Course)
            .join(Enrollment, Enrollment.course_id == Course.id)
            .where(Enrollment.student_id == user.id)
        )
        courses = course_result.scalars().all()
    else:
        course_result = await db.execute(
            select(Course).where(Course.teacher_id == user.id)
        ) if user.role == "teacher" else await db.execute(select(Course))
        courses = course_result.scalars().all()

    course_ids = [course.id for course in courses]
    course_names = {course.id: course.title for course in courses}
    events: list[dict] = []

    if course_ids:
        assignment_result = await db.execute(
            select(Assignment).where(
                Assignment.course_id.in_(course_ids),
                Assignment.due_date.is_not(None),
            )
        )
        for assignment in assignment_result.scalars().all():
            events.append({
                "id": str(assignment.id),
                "title": assignment.title,
                "course": course_names[assignment.course_id],
                "course_id": str(assignment.course_id),
                "date": assignment.due_date.isoformat(),
                "type": "assignment",
                "target": f"/student/assignments/{assignment.id}",
            })

        quiz_result = await db.execute(
            select(Quiz).where(
                Quiz.course_id.in_(course_ids),
                Quiz.due_date.is_not(None),
            )
        )
        for quiz in quiz_result.scalars().all():
            events.append({
                "id": str(quiz.id),
                "title": quiz.title,
                "course": course_names[quiz.course_id],
                "course_id": str(quiz.course_id),
                "date": quiz.due_date.isoformat(),
                "type": "quiz",
                "target": f"/student/quizzes/{quiz.id}",
            })

    custom_result = await db.execute(
        select(CalendarEvent).where(
            (CalendarEvent.user_id == user.id)
            | (CalendarEvent.user_id.is_(None))
            | (CalendarEvent.course_id.in_(course_ids) if course_ids else False)
        )
    )
    for event in custom_result.scalars().all():
        events.append({
            "id": str(event.id),
            "title": event.title,
            "course": course_names.get(event.course_id, "Platform"),
            "course_id": str(event.course_id) if event.course_id else None,
            "date": event.event_date.isoformat(),
            "type": "event",
            "target": None,
        })

    events.sort(key=lambda item: item["date"])
    return {"events": events}


@router.post("/calendar/events", status_code=status.HTTP_201_CREATED)
async def create_calendar_event(
    data: CalendarEventCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["teacher", "admin"])),
):
    if data.course_id:
        course = await db.get(Course, data.course_id)
        if course is None:
            raise HTTPException(status_code=404, detail="Course not found")
        if user.role == "teacher" and course.teacher_id != user.id:
            raise HTTPException(status_code=403, detail="You cannot manage this course")

    event = CalendarEvent(
        title=data.title,
        description=data.description,
        event_date=data.event_date,
        course_id=data.course_id,
        user_id=user.id,
    )
    db.add(event)
    await db.flush()
    return {"id": str(event.id), "title": event.title}
