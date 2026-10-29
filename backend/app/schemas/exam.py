from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ExamType(str, Enum):
    MID_SEMESTER = "MID_SEMESTER"
    END_SEMESTER = "END_SEMESTER"


class QuestionConfig(BaseModel):
    question_id: str = Field(..., description="Unique question identifier (e.g. Q1a, Q2)")
    display_name: str = Field(..., description="Human-readable label (e.g. Q1(a), Q2)")
    max_marks: float = Field(..., gt=0, description="Maximum marks attainable for this question")
    parent_question: Optional[str] = Field(None, description="Optional parent question ID (e.g. Q1)")


class ExamBase(BaseModel):
    title: Optional[str] = None
    subject_code: str = Field(..., min_length=2, max_length=15)
    subject_name: str = Field(..., min_length=2, max_length=100)
    exam_type: ExamType = ExamType.MID_SEMESTER
    semester: int = Field(..., ge=1, le=8)
    academic_year: str = Field(default="2025-2026")
    exam_date: str = Field(..., description="Date of the exam (YYYY-MM-DD)")
    questions: List[QuestionConfig] = Field(..., min_length=1)

    @field_validator("questions")
    @classmethod
    def validate_unique_questions(cls, questions: List[QuestionConfig]) -> List[QuestionConfig]:
        ids = [q.question_id for q in questions]
        if len(ids) != len(set(ids)):
            raise ValueError("All question_ids in an examination must be unique.")
        return questions


class ExamCreate(ExamBase):
    pass


class ExamResponse(ExamBase):
    exam_id: str
    total_marks: float
    created_by: str = "FAC001"
    created_at: str
    updated_at: str
    marks_count: Optional[int] = 0
