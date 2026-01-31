from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Existing settings
    ENVIRONMENT: str = 'development'
    ALLOW_ORIGINS: str = '*'
    GROQ_API_KEY: str
    DEEPGRAM_API_KEY: str
    LLM: str = 'llama-3.1-8b-instant'
    
    # Database settings
    DATABASE_URL: str = 'sqlite:///./interview_system.db'
    
    # Security settings
    SECRET_KEY: str = 'your-secret-key-change-in-production'
    ADMIN_USERNAME: str = 'admin'
    ADMIN_PASSWORD: str = 'admin123'
    
    # Interview settings
    INTERVIEW_TIMEOUT: int = 1800  # 30 minutes in seconds
    PASSING_SCORE: float = 70.0
    
    # Logging
    LOG_LEVEL: str = 'INFO'
    LOG_FILE: str = 'logs/app.log'

    model_config = SettingsConfigDict(env_file='.env')

settings = Settings()