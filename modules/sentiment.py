# modules/sentiment.py
import asyncio
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from core.logger import logger
from typing import Optional

# Initialize VADER analyzer once
try:
    _vader_analyzer = SentimentIntensityAnalyzer()
    logger.info("VADER SentimentIntensityAnalyzer initialized for general sentiment.")
except Exception as e:
    logger.error("Failed to initialize VADER SentimentIntensityAnalyzer.", extra={"error": str(e)}, exc_info=True)
    _vader_analyzer = None

class Sentiment:
    @staticmethod
    async def analyze_sentiment_async(text: str) -> float:
        """
        Analyzes the sentiment of a given text using VADER.
        Returns a compound score between -1 (most negative) and 1 (most positive).
        Returns 0.0 on error or if VADER is not available.
        Wraps the blocking VADER call in asyncio.to_thread.
        """
        if not _vader_analyzer:
            logger.error("VADER analyzer not available. Cannot perform general sentiment analysis.")
            return 0.0 # Neutral score if VADER is unavailable

        if not text or not isinstance(text, str) or not text.strip(): # Suggestion 2.5.1
            logger.debug("analyze_sentiment_async called with empty or invalid text.")
            return 0.0 # Neutral for empty/invalid text

        log_extra = {"text_snippet": text[:100]}

        def _compute_sentiment_sync():
            """Synchronous part to be run in a thread."""
            try:
                sentiment_scores = _vader_analyzer.polarity_scores(text)
                return sentiment_scores.get('compound', 0.0)
            except Exception as e_inner:
                logger.error(
                    "Error during VADER polarity_scores computation.",
                    extra={**log_extra, "error": str(e_inner)},
                    exc_info=True
                )
                return 0.0 # Return neutral on internal VADER error
        
        try:
            compound_score = await asyncio.to_thread(_compute_sentiment_sync)
            logger.debug(f"General sentiment for text '{log_extra['text_snippet']}...': {compound_score:.3f}")
            return compound_score
        except Exception as e_outer: # Catch errors from asyncio.to_thread itself or other issues
            logger.error(
                "Outer error in analyze_sentiment_async when calling VADER via to_thread.",
                extra={**log_extra, "error": str(e_outer)},
                exc_info=True
            )
            return 0.0 # Fallback to neutral on any error

# Note: The prompt for v2.7 mentioned "optionally support using a remote API if VADER fails."
# This is not implemented in this iteration but could be added here with additional settings.
