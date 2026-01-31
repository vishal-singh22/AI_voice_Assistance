from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app import crud, schemas, auth
from app.database import get_db
from app.config import settings
from app import models
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/admin', tags=['admin'])
templates = Jinja2Templates(directory='templates')

# ========== Dashboard ==========

@router.get('/', response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Admin dashboard home page"""
    return templates.TemplateResponse('admin/dashboard.html', {'request': request})

@router.get('/create-interview', response_class=HTMLResponse)
async def create_interview_page(request: Request):
    """Page to create new interview"""
    return templates.TemplateResponse('admin/create_interview.html', {'request': request})

@router.get('/candidates', response_class=HTMLResponse)
async def view_candidates_page(request: Request, db: Session = Depends(get_db)):
    """Page to view all candidates"""
    candidates = crud.get_all_candidates(db)
    
    # Format candidate data for display
    candidate_data = []
    for c in candidates:
        candidate_data.append({
            'id': c.id,
            'name': c.name,
            'email': c.contact_email,  # CHANGED: Show contact email
            'role': c.interview.role if c.interview else 'N/A',
            'total_questions': c.total_questions,
            'score': c.score,
            'passed': c.passed,
            'completed': c.has_completed
        })
    
    return templates.TemplateResponse(
        'admin/candidates.html',
        {'request': request, 'candidates': candidate_data}
    )

# ========== API Endpoints ==========

@router.post('/api/interviews', response_model=dict)
async def create_interview(
    interview: schemas.InterviewCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Create a new interview and candidate"""
    try:
        # Extract candidate info
        candidate_name = interview.candidate_name
        contact_email = interview.candidate_email
        
        # Create interview (exclude candidate fields)
        db_interview = models.Interview(
            name=interview.name,
            role=interview.role,
            num_questions=interview.num_questions,
            use_llm=interview.use_llm
        )
        db.add(db_interview)
        db.commit()
        db.refresh(db_interview)
        
        # Auto-generate LOGIN credentials
        login_email = auth.generate_email(candidate_name, db_interview.id)
        candidate_password = auth.generate_password()
        
        # Create candidate with BOTH emails
        candidate = crud.create_candidate(
            db,
            interview_id=db_interview.id,
            name=candidate_name,
            email=login_email,  # Auto-generated login email
            contact_email=contact_email,  # Real contact email from form
            password=candidate_password
        )
        
        # Generate interview URL
        base_url = str(request.base_url).rstrip('/')
        interview_url = f"{base_url}/candidate/login"
        
        logger.info(f'Interview created: {db_interview.name} with candidate: {candidate_name} (Login: {login_email}, Contact: {contact_email})')
        
        return {
            'success': True,
            'interview_id': db_interview.id,
            'candidate': {
                'email': login_email,  # Show login email in modal
                'password': candidate_password,
                'interview_url': interview_url
            }
        }
    
    except Exception as e:
        logger.error(f'Error creating interview: {e}')
        raise HTTPException(status_code=500, detail=str(e))

    
@router.get('/api/interviews', response_model=list[schemas.InterviewResponse])
async def get_interviews(db: Session = Depends(get_db)):
    """Get all interviews"""
    return crud.get_interviews(db)

@router.get('/api/candidates', response_model=list)
async def get_candidates(db: Session = Depends(get_db)):
    """Get all candidates with details"""
    candidates = crud.get_all_candidates(db)
    
    result = []
    for c in candidates:
        result.append({
            'id': c.id,
            'name': c.name,
            'email': c.contact_email,  # CHANGED: Show contact email instead of login email
            'role': c.interview.role if c.interview else 'N/A',
            'total_questions': c.total_questions,
            'score': c.score,
            'passed': c.passed,
            'completed': c.has_completed,
            'started_at': c.started_at.isoformat() if c.started_at else None,
            'completed_at': c.completed_at.isoformat() if c.completed_at else None
        })
    
    return result

@router.delete('/api/candidates/{candidate_id}')
async def delete_candidate(candidate_id: int, db: Session = Depends(get_db)):
    """Soft delete a candidate"""
    success = crud.soft_delete_candidate(db, candidate_id)
    if not success:
        raise HTTPException(status_code=404, detail='Candidate not found')
    return {'success': True, 'message': 'Candidate removed'}

@router.get('/api/candidates/{candidate_id}/details')
async def get_candidate_details(candidate_id: int, db: Session = Depends(get_db)):
    """Get detailed results for a candidate"""
    candidate = crud.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail='Candidate not found')
    
    responses = crud.get_responses_by_candidate(db, candidate_id)
    
    return {
        'candidate': {
            'name': candidate.name,
            'email': candidate.contact_email,  # CHANGED: Show contact email
            'role': candidate.interview.role if candidate.interview else 'N/A',
            'score': candidate.score,
            'passed': candidate.passed
        },
        'responses': [
            {
                'question': r.question_text,
                'answer': r.answer_text,
                'score': r.score,
                'keywords_found': r.keywords_found
            }
            for r in responses
        ]
    }