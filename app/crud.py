from sqlalchemy.orm import Session
from sqlalchemy import and_
from app import models, schemas
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ========== Interview CRUD ==========

def create_interview(db: Session, interview: schemas.InterviewCreate) -> models.Interview:
    """Create a new interview template"""
    db_interview = models.Interview(**interview.model_dump())
    db.add(db_interview)
    db.commit()
    db.refresh(db_interview)
    logger.info(f'Created interview: {db_interview.name} (ID: {db_interview.id})')
    return db_interview

def get_interview(db: Session, interview_id: int) -> models.Interview:
    """Get interview by ID"""
    return db.query(models.Interview).filter(models.Interview.id == interview_id).first()

def get_interviews(db: Session, skip: int = 0, limit: int = 100) -> list:
    """Get all interviews"""
    return db.query(models.Interview).offset(skip).limit(limit).all()

# ========== Candidate CRUD ==========

def create_candidate(
    db: Session,
    interview_id: int,
    name: str,
    email: str,
    contact_email: str,  # NEW parameter
    password: str
) -> models.Candidate:
    """Create a new candidate"""
    interview = get_interview(db, interview_id)
    
    db_candidate = models.Candidate(
        interview_id=interview_id,
        name=name,
        email=email,  # Login email (auto-generated)
        contact_email=contact_email,  # NEW: Real contact email
        password=password,
        total_questions=interview.num_questions if interview else 0
    )
    db.add(db_candidate)
    db.commit()
    db.refresh(db_candidate)
    logger.info(f'Created candidate: {name} ({email}) - Contact: {contact_email}')
    return db_candidate

    
def get_candidate_by_email(db: Session, email: str) -> models.Candidate:
    """Get candidate by email"""
    return db.query(models.Candidate).filter(
        and_(
            models.Candidate.email == email,
            models.Candidate.is_deleted == False
        )
    ).first()

def get_candidate(db: Session, candidate_id: int) -> models.Candidate:
    """Get candidate by ID"""
    return db.query(models.Candidate).filter(
        and_(
            models.Candidate.id == candidate_id,
            models.Candidate.is_deleted == False
        )
    ).first()

def get_candidates_by_interview(db: Session, interview_id: int) -> list:
    """Get all candidates for an interview"""
    return db.query(models.Candidate).filter(
        and_(
            models.Candidate.interview_id == interview_id,
            models.Candidate.is_deleted == False
        )
    ).all()

def get_all_candidates(db: Session) -> list:
    """Get all active candidates"""
    return db.query(models.Candidate).filter(
        models.Candidate.is_deleted == False
    ).all()

def update_candidate_status(
    db: Session,
    candidate_id: int,
    has_started: bool = None,
    has_completed: bool = None,
    score: float = None,
    passed: bool = None
) -> models.Candidate:
    """Update candidate status"""
    candidate = get_candidate(db, candidate_id)
    if not candidate:
        return None
    
    if has_started is not None:
        candidate.has_started = has_started
        if has_started and not candidate.started_at:
            candidate.started_at = datetime.utcnow()
    
    if has_completed is not None:
        candidate.has_completed = has_completed
        if has_completed and not candidate.completed_at:
            candidate.completed_at = datetime.utcnow()
    
    if score is not None:
        candidate.score = score
    
    if passed is not None:
        candidate.passed = passed
    
    db.commit()
    db.refresh(candidate)
    return candidate

def soft_delete_candidate(db: Session, candidate_id: int) -> bool:
    """Soft delete a candidate"""
    candidate = db.query(models.Candidate).filter(
        models.Candidate.id == candidate_id
    ).first()
    
    if not candidate:
        return False
    
    candidate.is_deleted = True
    db.commit()
    logger.info(f'Soft deleted candidate: {candidate.email}')
    return True

# ========== Response CRUD ==========

def create_response(
    db: Session,
    candidate_id: int,
    question_text: str,
    answer_text: str,
    score: float,
    keywords_found: list = None
) -> models.Response:
    """Create a new response"""
    db_response = models.Response(
        candidate_id=candidate_id,
        question_text=question_text,
        answer_text=answer_text,
        score=score,
        keywords_found=keywords_found or []
    )
    db.add(db_response)
    db.commit()
    db.refresh(db_response)
    return db_response

def get_responses_by_candidate(db: Session, candidate_id: int) -> list:
    """Get all responses for a candidate"""
    return db.query(models.Response).filter(
        models.Response.candidate_id == candidate_id
    ).all()

def calculate_final_score(db: Session, candidate_id: int) -> float:
    """Calculate final score for candidate"""
    responses = get_responses_by_candidate(db, candidate_id)
    if not responses:
        return 0.0
    
    total_score = sum(r.score for r in responses)
    avg_score = total_score / len(responses)
    return round(avg_score, 2)