import json
import random
import logging
from pathlib import Path
from typing import List, Dict

logger = logging.getLogger(__name__)

# Path to questions JSON file
QUESTIONS_FILE = Path('data/questions.json')

def load_questions() -> Dict:
    """Load questions from JSON file"""
    try:
        if not QUESTIONS_FILE.exists():
            logger.warning(f'Questions file not found: {QUESTIONS_FILE}')
            return {}
        
        with open(QUESTIONS_FILE, 'r') as f:
            questions = json.load(f)
        return questions
    except Exception as e:
        logger.error(f'Error loading questions: {e}')
        return {}

def get_questions_for_role(role: str, num_questions: int) -> List[Dict]:
    """Get random questions for a specific role"""
    questions_db = load_questions()
    
    # Get questions for the role (case-insensitive)
    role_lower = role.lower()
    role_questions = questions_db.get(role_lower, [])
    
    if not role_questions:
        logger.warning(f'No questions found for role: {role}')
        return []
    
    # Ensure we don't request more questions than available
    num_to_select = min(num_questions, len(role_questions))
    
    # Select random questions without replacement
    selected = random.sample(role_questions, num_to_select)
    logger.info(f'Selected {len(selected)} questions for role: {role}')
    return selected

def get_question_keywords(question: Dict) -> List[str]:
    """Extract keywords from a question object"""
    return question.get('keywords', [])

def format_question_prompt(question: Dict) -> str:
    """Format a question for the LLM or display"""
    return question.get('question', '')

# Default questions if file doesn't exist
DEFAULT_QUESTIONS = {
    "software_engineer": [
        {
            "question": "What is the difference between a list and a tuple in Python?",
            "keywords": ["immutable", "mutable", "performance", "hashable", "list", "tuple"]
        },
        {
            "question": "Explain the concept of object-oriented programming.",
            "keywords": ["encapsulation", "inheritance", "polymorphism", "abstraction", "class", "object"]
        },
        {
            "question": "What is a REST API and how does it work?",
            "keywords": ["HTTP", "GET", "POST", "stateless", "resource", "endpoint", "REST"]
        },
        {
            "question": "Describe the difference between SQL and NoSQL databases.",
            "keywords": ["relational", "schema", "scalability", "MongoDB", "PostgreSQL", "SQL"]
        },
        {
            "question": "What are design patterns and can you name a few?",
            "keywords": ["singleton", "factory", "observer", "strategy", "reusable", "solution"]
        },
        {
            "question": "Explain what version control is and why it's important.",
            "keywords": ["git", "commit", "branch", "merge", "collaboration", "history"]
        },
        {
            "question": "What is the difference between synchronous and asynchronous programming?",
            "keywords": ["async", "await", "blocking", "non-blocking", "concurrent", "parallel"]
        },
        {
            "question": "Describe the software development lifecycle.",
            "keywords": ["planning", "design", "development", "testing", "deployment", "maintenance"]
        }
    ],
    "data_scientist": [
        {
            "question": "What is the difference between supervised and unsupervised learning?",
            "keywords": ["labeled", "unlabeled", "classification", "clustering", "regression", "training"]
        },
        {
            "question": "Explain what overfitting means in machine learning.",
            "keywords": ["generalization", "training", "test", "validation", "complexity", "bias"]
        },
        {
            "question": "What is a neural network?",
            "keywords": ["layers", "neurons", "weights", "activation", "deep learning", "backpropagation"]
        },
        {
            "question": "Describe the purpose of cross-validation.",
            "keywords": ["validation", "k-fold", "training", "test", "model", "evaluation"]
        },
        {
            "question": "What is feature engineering and why is it important?",
            "keywords": ["features", "transform", "selection", "extraction", "preprocessing", "model"]
        },
        {
            "question": "Explain the difference between precision and recall.",
            "keywords": ["true positive", "false positive", "accuracy", "metrics", "classification"]
        },
        {
            "question": "What is gradient descent?",
            "keywords": ["optimization", "loss", "learning rate", "convergence", "minimize", "weights"]
        },
        {
            "question": "Describe what a confusion matrix is.",
            "keywords": ["true positive", "false positive", "true negative", "false negative", "classification"]
        }
    ],
    "product_manager": [
        {
            "question": "How do you prioritize features in a product roadmap?",
            "keywords": ["value", "impact", "effort", "stakeholders", "user", "business", "prioritization"]
        },
        {
            "question": "What is your approach to gathering user requirements?",
            "keywords": ["interview", "survey", "feedback", "user research", "stakeholder", "requirements"]
        },
        {
            "question": "Explain the difference between a product manager and a project manager.",
            "keywords": ["what", "why", "when", "how", "strategy", "execution", "vision"]
        },
        {
            "question": "How do you measure product success?",
            "keywords": ["metrics", "KPI", "user", "engagement", "revenue", "retention", "analytics"]
        },
        {
            "question": "Describe your experience with agile methodologies.",
            "keywords": ["scrum", "sprint", "standup", "backlog", "iteration", "agile"]
        },
        {
            "question": "How do you handle conflicts between stakeholders?",
            "keywords": ["communication", "compromise", "data", "priorities", "alignment", "negotiation"]
        },
        {
            "question": "What frameworks do you use for product strategy?",
            "keywords": ["OKR", "SWOT", "framework", "strategy", "goals", "vision"]
        },
        {
            "question": "How do you work with engineering teams?",
            "keywords": ["collaboration", "technical", "communication", "requirements", "trade-offs"]
        }
    ]
}

def create_default_questions_file():
    """Create default questions file if it doesn't exist"""
    try:
        QUESTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not QUESTIONS_FILE.exists():
            with open(QUESTIONS_FILE, 'w') as f:
                json.dump(DEFAULT_QUESTIONS, f, indent=2)
            logger.info(f'Created default questions file: {QUESTIONS_FILE}')
    except Exception as e:
        logger.error(f'Error creating questions file: {e}')