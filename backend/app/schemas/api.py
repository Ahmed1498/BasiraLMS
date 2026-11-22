from typing import Literal
from datetime import datetime
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator, model_validator


class CourseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=10000)
    category_id: str = Field(default="general", max_length=100)
    teacher_id: str | None = None


class ModuleCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    order_index: int = Field(default=0, ge=0)


class LessonCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content_type: Literal["text", "video", "file"] = "text"
    content_body: str = Field(default="", max_length=50000)
    video_url: AnyHttpUrl | None = None
    order_index: int = Field(default=0, ge=0)


class AssignmentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=10000)
    due_date: datetime | None = None
    total_points: int = Field(default=100, ge=1, le=10000)


class AssignmentSubmission(BaseModel):
    file_url: AnyHttpUrl | None = None
    submission_text: str | None = Field(default=None, max_length=50000)

    @model_validator(mode="after")
    def require_submission_content(self):
        if not (self.file_url and str(self.file_url).strip()) and not (
            self.submission_text and self.submission_text.strip()
        ):
            raise ValueError("Provide a submission link or text response")
        return self


class GradeSubmission(BaseModel):
    grade: float = Field(ge=0)
    feedback: str = Field(default="", max_length=10000)


class QuizQuestionCreate(BaseModel):
    question_text: str = Field(min_length=2, max_length=5000)
    options: list[str] = Field(min_length=2, max_length=10)
    correct_answer: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_correct_answer(self):
        if self.correct_answer not in self.options:
            raise ValueError("Correct answer must match one of the options")
        return self


class QuizCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=10000)
    time_limit_minutes: int = Field(default=30, ge=1, le=600)
    due_date: datetime | None = None
    questions: list[QuizQuestionCreate] = Field(min_length=1, max_length=100)


class QuizAttemptCreate(BaseModel):
    answers: dict[str, str] = Field(min_length=1, max_length=100)


class UserInvite(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    full_name: str = Field(min_length=2, max_length=200)
    role: Literal["student", "teacher"] = "student"

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1 or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return normalized


class UserUpdate(BaseModel):
    role: Literal["student", "teacher", "admin"] | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def require_change(self):
        if self.role is None and self.is_active is None:
            raise ValueError("Provide a role or account status change")
        return self


class AIChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=16000)
    page_context: dict[str, str | None] = Field(default_factory=dict)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SignupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=200)
    role: Literal["student", "teacher"]

    @field_validator("email")
    @classmethod
    def validate_signup_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1 or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return normalized


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def validate_forgot_password_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized.count("@") != 1 or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Enter a valid email address")
        return normalized


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class AdminBootstrapRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=128)
