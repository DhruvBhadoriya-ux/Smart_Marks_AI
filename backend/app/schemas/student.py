from typing import Optional, List
from pydantic import BaseModel, Field, EmailStr


class StudentBase(BaseModel):
    student_id: str = Field(..., min_length=2, max_length=25, description="Roll number or student enrollment ID")
    name: str = Field(..., min_length=2, max_length=100)
    semester: int = Field(..., ge=1, le=8)
    branch: str = Field(..., min_length=2, max_length=100)
    email: Optional[str] = None


class StudentCreate(StudentBase):
    pass


class StudentResponse(StudentBase):
    created_at: str


class StudentBatchImport(BaseModel):
    students: List[StudentCreate]
