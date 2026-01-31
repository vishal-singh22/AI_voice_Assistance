from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.database import SessionLocal
from app import crud
from app.interview_assistant import InterviewAssistant
from app.config import settings
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=['interview'])

@router.websocket('/interview/{candidate_id}')
async def websocket_interview(websocket: WebSocket, candidate_id: int):
    """WebSocket endpoint for conducting voice interviews"""
    await websocket.accept()
    
    db = SessionLocal()
    try:
        # Get candidate and interview details
        candidate = crud.get_candidate(db, candidate_id)
        if not candidate:
            await websocket.close(code=4004, reason='Candidate not found')
            return
        
        if candidate.has_completed:
            await websocket.close(code=4000, reason='Interview already completed')
            return
        
        interview = candidate.interview
        if not interview:
            await websocket.close(code=4004, reason='Interview not found')
            return
        
        # Prepare interview configuration
        interview_config = {
            'role': interview.role,
            'num_questions': interview.num_questions,
            'use_llm': interview.use_llm
        }
        
        logger.info(f'Starting interview for candidate {candidate_id} ({candidate.email})')
        
        # Create and run interview assistant
        assistant = InterviewAssistant(websocket, candidate_id, interview_config)
        
        try:
            await asyncio.wait_for(assistant.run(), timeout=settings.INTERVIEW_TIMEOUT)
        except asyncio.TimeoutError:
            logger.warning(f'Interview timeout for candidate {candidate_id}')
            await websocket.send_json({
                'type': 'timeout',
                'message': 'Interview time limit reached'
            })
            # Still calculate score from answered questions
            final_score = crud.calculate_final_score(db, candidate_id)
            passed = final_score >= settings.PASSING_SCORE
            crud.update_candidate_status(
                db,
                candidate_id,
                has_completed=True,
                score=final_score,
                passed=passed
            )
    
    except WebSocketDisconnect:
        logger.info(f'WebSocket disconnected for candidate {candidate_id}')
    except Exception as e:
        logger.error(f'Interview error for candidate {candidate_id}: {e}')
        try:
            await websocket.send_json({
                'type': 'error',
                'message': 'An error occurred during the interview'
            })
        except:
            pass
    finally:
        db.close()