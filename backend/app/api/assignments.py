from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.models import Assignment, Course, Enrollment, Submission, User
from app.schemas.api import AssignmentCreate, AssignmentSubmission, GradeSubmission

router = APIRouter(prefix="/api/v1", tags=["Assignments & Submissions"])


async def require_course_access(course_id: UUID, user: User, db: AsyncSession) -> Course:
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    if user.role == "teacher" and course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="You cannot access this course")
    if user.role == "student":
        enrollment = await db.execute(
            select(Enrollment.id).where(
                Enrollment.course_id == course_id,
                Enrollment.student_id == user.id,
            )
        )
        if enrollment.scalar_one_or_none() is None:
            raise HTTPException(status_code=403, detail="Enroll in the course first")
    return course


@router.get("/courses/{course_id}/assignments")
async def list_assignments(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await require_course_access(course_id, user, db)
    result = await db.execute(
        select(Assignment)
        .where(Assignment.course_id == course_id)
        .options(selectinload(Assignment.submissions))
        .order_by(Assignment.due_date.asc().nullslast())
    )
    assignments = result.scalars().all()
    return {
        "assignments": [
            {
                "id": str(assignment.id),
                "title": assignment.title,
                "description": assignment.description,
                "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
                "total_points": assignment.total_points,
                "my_submission": next(
                    (
                        {
                            "id": str(submission.id),
                            "status": submission.status,
                            "grade": submission.grade,
                            "feedback": submission.feedback,
                            "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                        }
                        for submission in assignment.submissions
                        if submission.student_id == user.id
                    ),
                    None,
                ) if user.role == "student" else None,
            }
            for assignment in assignments
        ]
    }


@router.post("/courses/{course_id}/assignments", status_code=status.HTTP_201_CREATED)
async def create_assignment(
    course_id: UUID,
    data: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["teacher", "admin"])),
):
    await require_course_access(course_id, user, db)
    assignment = Assignment(
        course_id=course_id,
        title=data.title,
        description=data.description,
        due_date=data.due_date,
        total_points=data.total_points,
    )
    db.add(assignment)
    await db.flush()
    return {"id": str(assignment.id), "title": assignment.title}


@router.get("/assignments/{assignment_id}")
async def get_assignment(
    assignment_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assignment = await db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await require_course_access(assignment.course_id, user, db)
    my_submission = None
    if user.role == "student":
        result = await db.execute(
            select(Submission).where(
                Submission.assignment_id == assignment_id,
                Submission.student_id == user.id,
            )
        )
        submission = result.scalar_one_or_none()
        if submission is not None:
            my_submission = {
                "id": str(submission.id),
                "status": submission.status,
                "grade": submission.grade,
                "feedback": submission.feedback,
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                "file_url": submission.file_url,
                "submission_text": submission.submission_text,
            }
    return {
        "id": str(assignment.id),
        "course_id": str(assignment.course_id),
        "title": assignment.title,
        "description": assignment.description,
        "due_date": assignment.due_date.isoformat() if assignment.due_date else None,
        "total_points": assignment.total_points,
        "my_submission": my_submission,
    }


@router.post("/assignments/{assignment_id}/submit", status_code=status.HTTP_201_CREATED)
async def submit_assignment(
    assignment_id: UUID,
    data: AssignmentSubmission,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["student"])),
):
    assignment = await db.get(Assignment, assignment_id)
    if assignment is None:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await require_course_access(assignment.course_id, user, db)

    existing = await db.execute(
        select(Submission).where(
            Submission.assignment_id == assignment_id,
            Submission.student_id == user.id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="You have already submitted this assignment")

    submission = Submission(
        assignment_id=assignment_id,
        student_id=user.id,
        file_url=str(data.file_url).strip() if data.file_url else None,
        submission_text=data.submission_text.strip() if data.submission_text else None,
        status="submitted",
    )
    db.add(submission)
    await db.flush()
    return {"id": str(submission.id), "status": submission.status}


@router.get("/courses/{course_id}/submissions")
async def list_course_submissions(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["teacher", "admin"])),
):
    await require_course_access(course_id, user, db)
    result = await db.execute(
        select(Submission)
        .join(Assignment, Submission.assignment_id == Assignment.id)
        .where(Assignment.course_id == course_id)
        .options(selectinload(Submission.student), selectinload(Submission.assignment))
        .order_by(Submission.submitted_at.desc())
    )
    submissions = result.scalars().all()
    return {
        "submissions": [
            {
                "id": str(submission.id),
                "assignment_id": str(submission.assignment_id),
                "assignment_title": submission.assignment.title,
                "student_id": str(submission.student_id),
                "student_name": submission.student.full_name,
                "student_email": submission.student.email,
                "submitted_at": submission.submitted_at.isoformat() if submission.submitted_at else None,
                "file_url": submission.file_url,
                "submission_text": submission.submission_text,
                "status": submission.status,
                "grade": submission.grade,
                "feedback": submission.feedback,
                "total_points": submission.assignment.total_points,
            }
            for submission in submissions
        ]
    }


@router.post("/submissions/{submission_id}/grade")
async def grade_submission(
    submission_id: UUID,
    data: GradeSubmission,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["teacher", "admin"])),
):
    result = await db.execute(
        select(Submission)
        .where(Submission.id == submission_id)
        .options(selectinload(Submission.assignment))
    )
    submission = result.scalar_one_or_none()
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    await require_course_access(submission.assignment.course_id, user, db)
    if data.grade > submission.assignment.total_points:
        raise HTTPException(
            status_code=422,
            detail=f"Grade cannot exceed {submission.assignment.total_points} points",
        )

    submission.grade = data.grade
    submission.feedback = data.feedback
    submission.status = "graded"
    await db.flush()
    return {"id": str(submission.id), "status": submission.status, "grade": submission.grade}
