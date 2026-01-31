from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# ========== Interview Schemas ==========

class InterviewCreate(BaseModel):
    name: str
    role: str
    num_questions: int
    use_llm: bool = False
    # Candidate fields (not stored in Interview table)
    candidate_name: str  # NEW: Real candidate name
    candidate_email: str  # NEW: Real contact email

class InterviewResponse(BaseModel):
    id: int
    name: str
    role: str
    num_questions: int
    use_llm: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========== Candidate Schemas ==========

class CandidateCreate(BaseModel):
    interview_id: int
    name: str

class CandidateResponse(BaseModel):
    id: int
    name: str
    email: str  # Login email (auto-generated)
    contact_email: str  # NEW: Real contact email
    role: str
    total_questions: int
    score: float
    passed: bool
    has_completed: bool
    
    class Config:
        from_attributes = True

class CandidateLogin(BaseModel):
    email: EmailStr
    password: str

class CandidateCredentials(BaseModel):
    email: str
    password: str
    interview_url: str

# ========== Response Schemas ==========

class ResponseCreate(BaseModel):
    candidate_id: int
    question_text: str
    answer_text: str
    score: float
    keywords_found: Optional[List[str]] = None

class ResponseDetail(BaseModel):
    id: int
    question_text: str
    answer_text: str
    score: float
    keywords_found: Optional[List[str]]
    created_at: datetime
    
    class Config:
        from_attributes = True

# ========== Result Schemas ==========

class InterviewResult(BaseModel):
    name: str
    email: str
    role: str
    total_questions: int
    score: float
    passed: bool
    responses: List[ResponseDetail]