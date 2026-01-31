import asyncio
import logging
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app import questions
from routers import admin, candidate, interview

# Setup logging
Path('logs').mkdir(exist_ok=True)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title='Voice Interview System',
    description='Production-ready voice-based interview platform',
    version='1.0.0'
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOW_ORIGINS.split(','),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
) 

# Mount static files
app.mount('/static', StaticFiles(directory='static'), name='static')

# Include routers
app.include_router(admin.router)
app.include_router(candidate.router)
app.include_router(interview.router)

@app.on_event('startup')
async def startup_event():
    """Initialize database and questions on startup"""
    logger.info('Starting Voice Interview System...')
    
    # Initialize database
    init_db()
    logger.info('Database initialized')
    
    # Create default questions file if needed
    questions.create_default_questions_file()
    logger.info('Questions loaded')
    
    logger.info('Application startup complete')

@app.head('/health')
@app.get('/health')
def health_check():
    """Health check endpoint"""
    return {'status': 'ok', 'environment': settings.ENVIRONMENT}

@app.get('/')
def root():
    """Root endpoint - redirect to admin dashboard"""
    

    return {
        'message': 'Voice Interview System API go on /admin pannel',
        'admin_dashboard': '/admin',
        'candidate_login': '/candidate/login',
        'health': '/health'
    }

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        'main:app',
        host='0.0.0.0',
        port=8000,
        reload=settings.ENVIRONMENT == 'development'
    )