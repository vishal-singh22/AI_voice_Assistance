from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Interview(Base):
    """Interview template created by admin"""
    __tablename__ = 'interviews'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    role = Column(String(100), nullable=False)
    num_questions = Column(Integer, nullable=False)
    use_llm = Column(Boolean, default=False)  # Toggle: LLM or DB questions
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    candidates = relationship('Candidate', back_populates='interview')


class Candidate(Base):
    """Candidate assigned to an interview"""
    __tablename__ = 'candidates'
    
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey('interviews.id'), nullable=False)
    name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)  # Login email (auto-generated)
    contact_email = Column(String(200), nullable=False)  # NEW: Real email for contact
    password = Column(String(200), nullable=False)
    
    # Interview status
    has_started = Column(Boolean, default=False)
    has_completed = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)  # Soft delete
    
    # Results
    total_questions = Column(Integer, default=0)
    score = Column(Float, default=0.0)
    passed = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    interview = relationship('Interview', back_populates='candidates')
    responses = relationship('Response', back_populates='candidate')

class Response(Base):
    """Individual question-answer pair with score"""
    __tablename__ = 'responses'
    
    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey('candidates.id'), nullable=False)
    
    question_text = Column(Text, nullable=False)
    answer_text = Column(Text, nullable=False)
    score = Column(Float, default=0.0)
    keywords_found = Column(JSON, nullable=True)  # Store matched keywords
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    candidate = relationship('Candidate', back_populates='responses')