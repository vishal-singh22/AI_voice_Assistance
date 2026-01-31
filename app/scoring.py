import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """Normalize text for keyword matching"""
    # Convert to lowercase
    text = text.lower()
    # Remove special characters but keep spaces
    text = re.sub(r'[^a-z0-9\s]', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

def calculate_keyword_score(answer: str, keywords: List[str]) -> Tuple[float, List[str]]:
    """
    Calculate score based on keyword matching
    Returns: (score, matched_keywords)
    """
    if not keywords or not answer:
        return 0.0, []
    
    # Normalize answer
    normalized_answer = normalize_text(answer)
    
    # Track matched keywords
    matched = []
    
    for keyword in keywords:
        normalized_keyword = normalize_text(keyword)
        # Check if keyword appears in answer
        if normalized_keyword in normalized_answer:
            matched.append(keyword)
    
    # Calculate score as percentage of matched keywords
    score = (len(matched) / len(keywords)) * 100
    
    logger.debug(f'Keyword matching: {len(matched)}/{len(keywords)} matched. Score: {score}')
    return round(score, 2), matched

def calculate_length_bonus(answer: str, min_words: int = 10) -> float:
    """
    Give bonus points for answers that are sufficiently detailed
    Returns: bonus score (0-10 points)
    """
    word_count = len(answer.split())
    
    if word_count < min_words:
        return 0.0
    elif word_count < 20:
        return 2.5
    elif word_count < 40:
        return 5.0
    else:
        return 10.0

def score_answer(answer: str, keywords: List[str]) -> Tuple[float, List[str]]:
    """
    Score an answer using simple keyword matching
    Returns: (final_score, matched_keywords)
    
    Scoring breakdown:
    - 90% from keyword matching
    - 10% from length bonus
    """
    if not answer or not answer.strip():
        return 0.0, []
    
    # Get keyword score (0-100)
    keyword_score, matched = calculate_keyword_score(answer, keywords)
    
    # Get length bonus (0-10)
    length_bonus = calculate_length_bonus(answer)
    
    # Weight: 90% keywords + 10% length
    final_score = (keyword_score * 0.9) + length_bonus
    
    # Ensure score is between 0 and 100
    final_score = min(100.0, max(0.0, final_score))
    
    logger.info(f'Answer scored: {final_score:.2f} (keywords: {keyword_score:.2f}, length: {length_bonus:.2f})')
    return round(final_score, 2), matched