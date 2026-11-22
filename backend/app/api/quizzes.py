from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.models import Course, Enrollment, Quiz, QuizAttempt, QuizQuestion, User
from app.schemas.api import QuizAttemptCreate, QuizCreate

router = APIRouter(prefix="/api/v1", tags=["Quizzes"])


async def require_quiz_course_access(course_id: UUID, user: User, db: AsyncSession) -> None:
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if user.role == "teacher" and course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="You cannot access this course")
    if user.role == "student":
        enrollment = await db.execute(
            select(Enrollment.id).where(
                Enrollment.student_id == user.id,
                Enrollment.course_id == course_id,
            )
        )
        if enrollment.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Enroll in the course first")


@router.get("/courses/{course_id}/quizzes")
async def list_quizzes(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_quiz_course_access(course_id, user, db)
    result = await db.execute(
        select(Quiz)
        .where(Quiz.course_id == course_id)
        .options(selectinload(Quiz.questions))
        .order_by(Quiz.id)
    )
    quizzes = result.scalars().all()
    return {
        "quizzes": [
            {
                "id": str(quiz.id),
                "title": quiz.title,
                "description": quiz.description,
                "time_limit_minutes": quiz.time_limit_minutes,
                "due_date": quiz.due_date.isoformat() if quiz.due_date else None,
                "question_count": len(quiz.questions),
            }
            for quiz in quizzes
        ]
    }


@router.post("/courses/{course_id}/quizzes", status_code=status.HTTP_201_CREATED)
async def create_quiz(
    course_id: UUID,
    data: QuizCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["teacher", "admin"])),
):
    await require_quiz_course_access(course_id, user, db)
    quiz = Quiz(
        course_id=course_id,
        title=data.title,
        description=data.description,
        time_limit_minutes=data.time_limit_minutes,
        due_date=data.due_date,
    )
    quiz.questions = [
        QuizQuestion(
            question_text=question.question_text,
            question_type="multiple_choice",
            options=question.options,
            correct_answer=question.correct_answer,
        )
        for question in data.questions
    ]
    db.add(quiz)
    await db.flush()
    return {"id": str(quiz.id), "title": quiz.title}


@router.get("/quizzes/{quiz_id}")
async def get_quiz(
    quiz_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Quiz).where(Quiz.id == quiz_id).options(selectinload(Quiz.questions))
    )
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    await require_quiz_course_access(quiz.course_id, user, db)
    return {
        "id": str(quiz.id),
        "title": quiz.title,
        "description": quiz.description,
        "time_limit_minutes": quiz.time_limit_minutes,
        "questions": [
            {
                "id": str(question.id),
                "question_text": question.question_text,
                "options": question.options or [],
            }
            for question in quiz.questions
        ],
    }


@router.post("/quizzes/{quiz_id}/attempt", status_code=status.HTTP_201_CREATED)
async def submit_quiz_attempt(
    quiz_id: UUID,
    data: QuizAttemptCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["student"])),
):
    result = await db.execute(
        select(Quiz).where(Quiz.id == quiz_id).options(selectinload(Quiz.questions))
    )
    quiz = result.scalar_one_or_none()
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    await require_quiz_course_access(quiz.course_id, user, db)
    if not quiz.questions:
        raise HTTPException(status_code=409, detail="This quiz has no questions")

    question_ids = {str(question.id) for question in quiz.questions}
    if not set(data.answers).issubset(question_ids):
        raise HTTPException(status_code=422, detail="Answers contain a question from another quiz")

    correct_count = sum(
        1
        for question in quiz.questions
        if data.answers.get(str(question.id)) == question.correct_answer
    )
    score = round(correct_count * 100 / len(quiz.questions), 2)
    attempt = QuizAttempt(
        quiz_id=quiz_id,
        student_id=user.id,
        score=score,
        answers=data.answers,
    )
    db.add(attempt)
    await db.flush()
    return {
        "id": str(attempt.id),
        "score": score,
        "correct_count": correct_count,
        "question_count": len(quiz.questions),
    }
