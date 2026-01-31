from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app import crud, schemas, auth
from app.database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/candidate', tags=['candidate'])
templates = Jinja2Templates(directory='templates')

# ========== Pages ==========

@router.get('/login', response_class=HTMLResponse)
async def login_page(request: Request):
    """Candidate login page"""
    return templates.TemplateResponse('candidate/login.html', {'request': request})

@router.post('/login')
async def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    """Handle candidate login"""
    candidate = crud.get_candidate_by_email(db, email)
    
    if not auth.verify_candidate(email, password, candidate):
        return templates.TemplateResponse(
            'candidate/login.html',
            {'request': {}, 'error': 'Invalid email or password'}
        )
    
    if candidate.has_completed:
        # Redirect to results if already completed
        return RedirectResponse(url=f'/candidate/result/{candidate.id}', status_code=303)
    
    # Redirect to instructions
    return RedirectResponse(url=f'/candidate/instructions/{candidate.id}', status_code=303)

@router.get('/instructions/{candidate_id}', response_class=HTMLResponse)
async def instructions_page(request: Request, candidate_id: int, db: Session = Depends(get_db)):
    """Pre-interview instructions page"""
    candidate = crud.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail='Candidate not found')
    
    interview = candidate.interview
    
    return templates.TemplateResponse(
        'candidate/instructions.html',
        {
            'request': request,
            'candidate': candidate,
            'interview': interview
        }
    )

@router.get('/interview/{candidate_id}', response_class=HTMLResponse)
async def interview_page(request: Request, candidate_id: int, db: Session = Depends(get_db)):
    """Voice interview page"""
    candidate = crud.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail='Candidate not found')
    
    if candidate.has_completed:
        return RedirectResponse(url=f'/candidate/result/{candidate_id}')
    
    return templates.TemplateResponse(
        'candidate/interview.html',
        {
            'request': request,
            'candidate_id': candidate_id
        }
    )

@router.get('/result/{candidate_id}', response_class=HTMLResponse)
async def result_page(request: Request, candidate_id: int, db: Session = Depends(get_db)):
    """Interview result page"""
    candidate = crud.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail='Candidate not found')
    
    if not candidate.has_completed:
        raise HTTPException(status_code=400, detail='Interview not completed yet')
    
    responses = crud.get_responses_by_candidate(db, candidate_id)
    
    # Create a candidate dict with contact_email for display
    candidate_display = {
        'name': candidate.name,
        'email': candidate.contact_email,  # CHANGED: Show contact email
        'score': candidate.score,
        'passed': candidate.passed
    }
    
    return templates.TemplateResponse(
        'candidate/result.html',
        {
            'request': request,
            'candidate': candidate_display,  # Pass modified dict
            'interview': candidate.interview,
            'responses': responses
        }
    )

    
# ========== API Endpoints ==========

@router.get('/api/status/{candidate_id}')
async def get_candidate_status(candidate_id: int, db: Session = Depends(get_db)):
    """Get candidate interview status"""
    candidate = crud.get_candidate(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail='Candidate not found')
    
    return {
        'has_started': candidate.has_started,
        'has_completed': candidate.has_completed,
        'score': candidate.score,
        'passed': candidate.passed
    }