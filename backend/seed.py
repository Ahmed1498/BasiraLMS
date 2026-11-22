import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.core.database import AsyncSessionLocal
from app.models.models import User, Course, Module, Lesson, Assignment, Quiz, QuizQuestion
from sqlalchemy.future import select

async def seed_rich_courses():
    async with AsyncSessionLocal() as session:
        print("Seeding rich production-ready courses into Basira LMS...")

        # 1. Find or create Dr. Sarah Ahmed (Teacher)
        t_result = await session.execute(select(User).where(User.email == "sarah.teacher@basira.com"))
        teacher = t_result.scalars().first()
        if not teacher:
            teacher = User(
                email="sarah.teacher@basira.com",
                full_name="Dr. Sarah Ahmed",
                role="teacher"
            )
            session.add(teacher)
            await session.commit()
            await session.refresh(teacher)

        # 2. Course 1: Python Programming Masterclass
        c1 = Course(
            title="Python Programming Masterclass: From Zero to Hero",
            description="Master Python 3 from fundamentals to advanced concepts including object-oriented programming, algorithms, and real-world applications.",
            category_id="programming",
            teacher_id=teacher.id
        )
        session.add(c1)
        await session.commit()
        await session.refresh(c1)

        # Module 1 for Course 1
        m1 = Module(course_id=c1.id, title="Module 1: Python Fundamentals & Syntax", order_index=1)
        session.add(m1)
        await session.commit()
        await session.refresh(m1)

        l1 = Lesson(
            module_id=m1.id,
            title="1.1 Introduction to Variables & Data Types",
            content_type="text",
            content_body="""# Welcome to Python Programming!
In this foundational lesson, we explore how data is stored, manipulated, and represented in computer memory.

## Key Concepts Covered:
1. **Variables**: Containers for storing data values. In Python, variables are dynamically typed (no explicit declaration needed).
2. **Primitive Data Types**:
   - `int`: Whole numbers (e.g., `42`)
   - `float`: Decimal numbers (e.g., `3.14159`)
   - `str`: Text strings enclosed in quotes (e.g., `"Hello, Basira!"`)
   - `bool`: Truth values (`True` or `False`)

### Code Example:
```python
# Variable assignment
student_name = "Ahmed Ali"
course_score = 95.5
is_passed = True

print(f"Student: {student_name}, Score: {course_score}, Passed: {is_passed}")
```""",
            order_index=1
        )
        session.add(l1)

        l2 = Lesson(
            module_id=m1.id,
            title="1.2 Video Lecture: Python Syntax & Operators",
            content_type="video",
            video_url="https://www.youtube.com/embed/_uQrJ0TkZlc",
            content_body="Watch this comprehensive video lecture explaining operators, precedence, and basic input/output operations in Python.",
            order_index=2
        )
        session.add(l2)

        # Module 2 for Course 1
        m2 = Module(course_id=c1.id, title="Module 2: Control Flow & Functions", order_index=2)
        session.add(m2)
        await session.commit()
        await session.refresh(m2)

        l3 = Lesson(
            module_id=m2.id,
            title="2.1 Conditional Statements (if/elif/else)",
            content_type="text",
            content_body="""# Making Decisions in Code
Conditional statements allow your program to execute different blocks of code based on whether a boolean expression evaluates to True or False.

### Syntax Structure:
```python
score = 88

if score >= 90:
    grade = 'A'
elif score >= 80:
    grade = 'B'
else:
    grade = 'C'

print(f"Your grade is: {grade}")
```""",
            order_index=1
        )
        session.add(l3)

        l4 = Lesson(
            module_id=m2.id,
            title="2.2 Video Lecture: Writing Reusable Functions",
            content_type="video",
            video_url="https://www.youtube.com/embed/BVfVKAXBZpc",
            content_body="Learn how to write modular code using Python functions.",
            order_index=2
        )
        session.add(l4)

        # Assignment for Course 1
        asn1 = Assignment(
            course_id=c1.id,
            title="Assignment 1: Build a Python Calculator",
            description="Create a command-line calculator in Python that supports addition, subtraction, multiplication, and division with error handling for division by zero.",
            total_points=100
        )
        session.add(asn1)

        # Quiz for Course 1
        qz1 = Quiz(
            course_id=c1.id,
            title="Python Basics Quiz",
            description="Test your knowledge of variables, data types, and conditionals.",
            time_limit_minutes=20
        )
        session.add(qz1)
        await session.commit()
        await session.refresh(qz1)

        q1 = QuizQuestion(
            quiz_id=qz1.id,
            question_text="Which keyword is used to define a function in Python?",
            question_type="multiple_choice",
            options=["func", "def", "function", "lambda"],
            correct_answer="def"
        )
        q2 = QuizQuestion(
            quiz_id=qz1.id,
            question_text="What is the output of `type(10)` in Python?",
            question_type="multiple_choice",
            options=["<class 'float'>", "<class 'int'>", "<class 'str'>", "<class 'number'>"],
            correct_answer="<class 'int'>"
        )
        session.add(q1)
        session.add(q2)

        # 3. Course 2: Web Development with Next.js & Tailwind
        c2 = Course(
            title="Full-Stack Web Development with Next.js & Tailwind CSS",
            description="Build modern, high-performance full-stack web applications using Next.js App Router, TypeScript, Tailwind CSS, and FastAPI.",
            category_id="web-development",
            teacher_id=teacher.id
        )
        session.add(c2)
        await session.commit()
        await session.refresh(c2)

        m3 = Module(course_id=c2.id, title="Module 1: Modern Frontend Architecture", order_index=1)
        session.add(m3)
        await session.commit()
        await session.refresh(m3)

        l5 = Lesson(
            module_id=m3.id,
            title="1.1 Introduction to Next.js App Router",
            content_type="text",
            content_body="""# Next.js App Router Architecture
Next.js is a React framework that enables server-side rendering, static site generation, and powerful routing capabilities out of the box.

## Key Features:
- **Server Components (RSCs)**: Rendered on the server to reduce client bundle size.
- **File-based Routing**: Folders and files in `app/` automatically map to URL routes.
- **API Routes & Server Actions**: Seamlessly execute backend logic right from your components.""",
            order_index=1
        )
        session.add(l5)

        l6 = Lesson(
            module_id=m3.id,
            title="1.2 Video Lecture: Building UIs with Tailwind CSS",
            content_type="video",
            video_url="https://www.youtube.com/embed/ft30zcMlFXw",
            content_body="Master utility-first CSS styling with Tailwind CSS for gorgeous, responsive user interfaces.",
            order_index=2
        )
        session.add(l6)

        await session.commit()
        print("Successfully seeded rich courses, modules, lessons, videos, assignments, and quizzes into Basira LMS!")

if __name__ == "__main__":
    asyncio.run(seed_rich_courses())
