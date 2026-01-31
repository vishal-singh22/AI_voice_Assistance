import secrets
import string
from app.config import settings

def generate_password(length: int = 12) -> str:
    """Generate a random password"""
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def generate_email(name: str, interview_id: int) -> str:
    """Generate email from name and interview ID"""
    # Remove spaces and special chars from name
    clean_name = ''.join(c for c in name if c.isalnum()).lower()
    # Add random suffix to ensure uniqueness
    suffix = ''.join(secrets.choice(string.digits) for _ in range(4))
    return f'{clean_name}{suffix}@interview.local'

def verify_admin(username: str, password: str) -> bool:
    """Verify admin credentials"""
    return (
        username == settings.ADMIN_USERNAME and
        password == settings.ADMIN_PASSWORD
    )

def verify_candidate(email: str, password: str, candidate) -> bool:
    """Verify candidate credentials"""
    if not candidate:
        return False
    return candidate.email == email and candidate.password == password