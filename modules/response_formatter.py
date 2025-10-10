# modules/response_formatter.py
from typing import Dict, Any, Optional
from core.logger import logger

def _get_sentiment_mood(score: Optional[float]) -> str:
    """Convert sentiment score to mood description"""
    if score is None or not isinstance(score, (int, float)):
        return "N/A"
    if score > 0.05:  
        return "Positive"
    elif score < -0.05: 
        return "Negative"
    else:
        return "Neutral"

def format_analyze_sentiment(sentiment_score: float, text_snippet: str = "") -> str:
    """Format sentiment analysis results for user presentation"""
    mood = _get_sentiment_mood(sentiment_score)
    
    if text_snippet:
        return f"The sentiment of '{text_snippet[:50]}...' appears to be {mood} (score: {sentiment_score:.2f})."
    else:
        return f"The sentiment appears to be {mood} (score: {sentiment_score:.2f})."

def format_error_message(user_message: str, technical_detail: Optional[str] = None) -> str:
    """
    Standard way to format error messages back to the user.
    Technical details are logged but not shown to user.
    """
    if technical_detail:
        logger.error(f"Error formatted for user. Technical detail: {technical_detail}")
    
    return f"Sorry, I encountered an issue: {user_message}"