from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.models import Assignment, Course, Enrollment, Lesson, LessonProgress, Module, User
from app.schemas.api import CourseCreate, LessonCreate, ModuleCreate

router = APIRouter(prefix="/api/v1/courses", tags=["Courses"])


async def require_course_editor(course_id: UUID, user: User, db: AsyncSession) -> Course:
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if user.role != "admin" and course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="You cannot manage this course")
    return course


@router.get("")
async def list_courses(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = (
        select(Course)
        .options(
            selectinload(Course.enrollments),
            selectinload(Course.modules).selectinload(Module.lessons),
            selectinload(Course.assignments).selectinload(Assignment.submissions),
        )
        .order_by(Course.created_at.desc())
    )
    if user.role == "teacher":
        query = query.where(Course.teacher_id == user.id)

    result = await db.execute(query)
    courses = result.scalars().all()
    progress_by_course: dict[UUID, int] = {}
    if user.role == "student":
        progress_result = await db.execute(
            select(Lesson.module_id, Module.course_id)
            .join(LessonProgress, LessonProgress.lesson_id == Lesson.id)
            .join(Module, Lesson.module_id == Module.id)
            .where(LessonProgress.student_id == user.id)
        )
        for _module_id, progress_course_id in progress_result.all():
            progress_by_course[progress_course_id] = progress_by_course.get(progress_course_id, 0) + 1
    return {
        "courses": [
            {
                "id": str(course.id),
                "title": course.title,
                "description": course.description,
                "category_id": course.category_id,
                "teacher_id": str(course.teacher_id) if course.teacher_id else None,
                "enrolled": any(enrollment.student_id == user.id for enrollment in course.enrollments),
                "student_count": len(course.enrollments),
                "lesson_count": sum(len(module.lessons) for module in course.modules),
                "completed_lessons": progress_by_course.get(course.id, 0),
                "pending_submissions": sum(
                    submission.status == "submitted"
                    for assignment in course.assignments
                    for submission in assignment.submissions
                ),
            }
            for course in courses
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_course(
    course_data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["teacher", "admin"])),
):
    teacher_id = user.id
    if user.role == "admin" and course_data.teacher_id:
        try:
            teacher_id = UUID(course_data.teacher_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid teacher identifier") from exc
        teacher = await db.get(User, teacher_id)
        if teacher is None or teacher.role != "teacher":
            raise HTTPException(status_code=400, detail="The selected owner is not a teacher")

    course = Course(
        title=course_data.title,
        description=course_data.description,
        category_id=course_data.category_id,
        teacher_id=teacher_id,
    )
    db.add(course)
    await db.flush()
    return {"id": str(course.id), "title": course.title}


@router.post("/{course_id}/enroll", status_code=status.HTTP_201_CREATED)
async def enroll_in_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["student"])),
):
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")

    result = await db.execute(
        select(Enrollment).where(
            Enrollment.course_id == course_id,
            Enrollment.student_id == user.id,
        )
    )
    enrollment = result.scalar_one_or_none()
    if enrollment is None:
        db.add(Enrollment(course_id=course_id, student_id=user.id))
        await db.flush()
    return {"enrolled": True}


@router.get("/{course_id}")
async def get_course_detail(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.modules).selectinload(Module.lessons))
    )
    course = result.scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if user.role == "teacher" and course.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="You cannot access this course")

    enrollment_result = await db.execute(
        select(Enrollment.id).where(
            Enrollment.course_id == course_id,
            Enrollment.student_id == user.id,
        )
    )
    completed_result = await db.execute(
        select(LessonProgress.lesson_id)
        .join(Lesson, LessonProgress.lesson_id == Lesson.id)
        .join(Module, Lesson.module_id == Module.id)
        .where(Module.course_id == course_id, LessonProgress.student_id == user.id)
    )
    completed_lesson_ids = {str(lesson_id) for lesson_id in completed_result.scalars().all()}
    return {
        "id": str(course.id),
        "title": course.title,
        "description": course.description,
        "category_id": course.category_id,
        "enrolled": enrollment_result.scalar_one_or_none() is not None,
        "completed_lesson_ids": sorted(completed_lesson_ids),
        "modules": [
            {
                "id": str(module.id),
                "title": module.title,
                "lessons": [
                    {
                        "id": str(lesson.id),
                        "title": lesson.title,
                        "content_type": lesson.content_type,
                        "content_body": lesson.content_body,
                        "video_url": lesson.video_url,
                    }
                    for lesson in sorted(module.lessons, key=lambda item: item.order_index or 0)
                ],
            }
            for module in sorted(course.modules, key=lambda item: item.order_index or 0)
        ],
    }


@router.post("/{course_id}/modules", status_code=status.HTTP_201_CREATED)
async def create_module(
    course_id: UUID,
    data: ModuleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["teacher", "admin"])),
):
    await require_course_editor(course_id, user, db)
    module = Module(course_id=course_id, title=data.title, order_index=data.order_index)
    db.add(module)
    await db.flush()
    return {"id": str(module.id), "title": module.title}


@router.post("/modules/{module_id}/lessons", status_code=status.HTTP_201_CREATED)
async def create_lesson(
    module_id: UUID,
    data: LessonCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["teacher", "admin"])),
):
    module = await db.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=404, detail="Module not found")
    await require_course_editor(module.course_id, user, db)
    lesson = Lesson(
        module_id=module_id,
        title=data.title,
        content_type=data.content_type,
        content_body=data.content_body,
        video_url=str(data.video_url) if data.video_url else None,
        order_index=data.order_index,
    )
    db.add(lesson)
    await db.flush()
    return {"id": str(lesson.id), "title": lesson.title}


@router.post("/lessons/{lesson_id}/complete")
async def complete_lesson(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_role(["student"])),
):
    result = await db.execute(
        select(Lesson).where(Lesson.id == lesson_id).options(selectinload(Lesson.module))
    )
    lesson = result.scalar_one_or_none()
    if lesson is None:
        raise HTTPException(status_code=404, detail="Lesson not found")

    enrollment = await db.execute(
        select(Enrollment.id).where(
            Enrollment.course_id == lesson.module.course_id,
            Enrollment.student_id == user.id,
        )
    )
    if enrollment.scalar_one_or_none() is None:
        raise HTTPException(status_code=403, detail="Enroll in the course before completing lessons")

    progress = await db.execute(
        select(LessonProgress.id).where(
            LessonProgress.lesson_id == lesson_id,
            LessonProgress.student_id == user.id,
        )
    )
    if progress.scalar_one_or_none() is None:
        db.add(LessonProgress(lesson_id=lesson_id, student_id=user.id))
        await db.flush()
    return {"lesson_id": str(lesson_id), "completed": True}
