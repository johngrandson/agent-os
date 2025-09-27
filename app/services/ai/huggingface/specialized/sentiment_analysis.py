"""
Sentiment Analysis Service using HuggingFace models.

Specialized service for analyzing customer feedback, support tickets,
and any text content to understand emotional tone and satisfaction.
"""

from typing import Any

from core.logger import get_module_logger

from ..huggingface_service import HuggingFaceService
from ..models.pipeline_factory import PipelineFactory
from ..models.result_types import Sentiment, SentimentAnalysisResult


logger = get_module_logger(__name__)


class SentimentAnalysisService(HuggingFaceService):
    """
    Service for analyzing sentiment in text content.

    Focuses on business value - understanding customer satisfaction,
    feedback tone, and emotional responses in support communications.
    """

    def __init__(self, model_variant: str = "default"):
        super().__init__()
        self.model_variant = model_variant
        self.pipeline_config = PipelineFactory.create_pipeline_config(
            "sentiment_analysis", model_variant
        )

    async def analyze_message(self, text: str) -> SentimentAnalysisResult:
        """
        Analyze sentiment of a single message or text.

        Args:
            text: Text content to analyze

        Returns:
            SentimentAnalysisResult with sentiment classification

        Example:
            result = await sentiment_service.analyze_message("I love this product!")
            print(f"Sentiment: {result.sentiment}, Score: {result.overall_score}")
        """
        logger.info("Analyzing message sentiment")

        if not text or not text.strip():
            return self._create_neutral_result("Empty or invalid text")

        # Get sentiment pipeline
        pipeline = await self.get_pipeline(
            self.pipeline_config["hf_task"], self.pipeline_config["model_id"]
        )

        # Run sentiment analysis
        result = await self._run_pipeline(pipeline, text.strip())

        return self._process_sentiment_result(result, text)

    async def analyze_customer_feedback(
        self, feedback: str, context: dict | None = None
    ) -> SentimentAnalysisResult:
        """
        Analyze customer feedback with business context.

        Args:
            feedback: Customer feedback text
            context: Optional context (product, service type, etc.)

        Returns:
            SentimentAnalysisResult optimized for customer feedback
        """
        logger.info("Analyzing customer feedback sentiment")

        # Enhance feedback with context for better analysis
        if context:
            enhanced_feedback = self._enhance_feedback_with_context(feedback, context)
        else:
            enhanced_feedback = feedback

        return await self.analyze_message(enhanced_feedback)

    async def analyze_support_ticket(
        self, ticket_content: str, priority: str | None = None
    ) -> SentimentAnalysisResult:
        """
        Analyze support ticket sentiment to help prioritize responses.

        Args:
            ticket_content: Support ticket content
            priority: Optional existing priority level

        Returns:
            SentimentAnalysisResult with support-specific insights
        """
        logger.info("Analyzing support ticket sentiment")

        # Clean and prepare ticket content
        cleaned_content = self._clean_support_ticket_content(ticket_content)

        result = await self.analyze_message(cleaned_content)

        # Adjust interpretation for support context
        result = self._adjust_for_support_context(result, priority)

        return result

    async def batch_analyze(self, texts: list[str]) -> list[SentimentAnalysisResult]:
        """
        Analyze sentiment for multiple texts efficiently.

        Args:
            texts: List of text content to analyze

        Returns:
            List of SentimentAnalysisResult in same order as input
        """
        logger.info(f"Batch analyzing sentiment for {len(texts)} texts")

        results = []
        for text in texts:
            try:
                result = await self.analyze_message(text)
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing text sentiment: {e}")
                results.append(self._create_neutral_result(f"Analysis error: {str(e)}"))

        return results

    async def get_satisfaction_score(self, feedback: str) -> float:
        """
        Get a simple satisfaction score (0.0 to 1.0) from feedback.

        Args:
            feedback: Customer feedback text

        Returns:
            Satisfaction score between 0.0 (very unsatisfied) and 1.0 (very satisfied)
        """
        result = await self.analyze_message(feedback)

        # Convert sentiment to satisfaction score
        if result.sentiment == Sentiment.POSITIVE:
            return 0.5 + (result.confidence * 0.5)  # 0.5 to 1.0
        elif result.sentiment == Sentiment.NEGATIVE:
            return 0.5 - (result.confidence * 0.5)  # 0.0 to 0.5
        else:
            return 0.5  # Neutral

    def _enhance_feedback_with_context(self, feedback: str, context: dict) -> str:
        """Enhance feedback text with business context for better analysis."""
        enhanced_parts = [feedback]

        if "product" in context:
            enhanced_parts.append(f"Product: {context['product']}")

        if "service_type" in context:
            enhanced_parts.append(f"Service: {context['service_type']}")

        return " | ".join(enhanced_parts)

    def _clean_support_ticket_content(self, content: str) -> str:
        """Clean support ticket content for better sentiment analysis."""
        # Remove common ticket artifacts
        cleaned = content.replace("Ticket ID:", "").replace("Reference:", "")

        # Focus on the actual message content
        lines = [line.strip() for line in cleaned.split("\n") if line.strip()]

        # Filter out system messages and headers
        content_lines = []
        for line in lines:
            if not any(header in line.lower() for header in ["from:", "to:", "subject:", "date:"]):
                content_lines.append(line)

        return " ".join(content_lines)

    def _adjust_for_support_context(
        self, result: SentimentAnalysisResult, priority: str | None
    ) -> SentimentAnalysisResult:
        """Adjust sentiment result for support ticket context."""
        # In support context, neutral might actually indicate frustration
        if result.sentiment == Sentiment.NEUTRAL and result.confidence < 0.7:
            # Lower confidence neutral in support context might be subtle negativity
            result.negative_score += 0.1
            if result.negative_score > result.positive_score:
                result.sentiment = Sentiment.NEGATIVE

        return result

    def _process_sentiment_result(
        self, raw_result: Any, original_text: str
    ) -> SentimentAnalysisResult:
        """Process raw model result into structured SentimentAnalysisResult."""
        try:
            positive_score = 0.0
            negative_score = 0.0
            neutral_score = 0.0
            confidence = 0.0
            sentiment = Sentiment.NEUTRAL

            if isinstance(raw_result, list) and raw_result:
                # Standard sentiment analysis format
                result_item = raw_result[0] if isinstance(raw_result[0], dict) else raw_result[0]

                if isinstance(result_item, dict):
                    label = result_item.get("label", "").upper()
                    score = result_item.get("score", 0.0)

                    # Map model labels to our sentiment categories
                    if "POSITIVE" in label or "POS" in label:
                        sentiment = Sentiment.POSITIVE
                        positive_score = score
                        negative_score = 1.0 - score
                    elif "NEGATIVE" in label or "NEG" in label:
                        sentiment = Sentiment.NEGATIVE
                        negative_score = score
                        positive_score = 1.0 - score
                    else:
                        sentiment = Sentiment.NEUTRAL
                        neutral_score = score
                        positive_score = (1.0 - score) / 2
                        negative_score = (1.0 - score) / 2

                    confidence = score

                elif isinstance(raw_result, list) and len(raw_result) >= 2:
                    # Multiple scores format
                    for item in raw_result:
                        if isinstance(item, dict):
                            label = item.get("label", "").upper()
                            score = item.get("score", 0.0)

                            if "POSITIVE" in label:
                                positive_score = score
                            elif "NEGATIVE" in label:
                                negative_score = score
                            elif "NEUTRAL" in label:
                                neutral_score = score

                    # Determine dominant sentiment
                    max_score = max(positive_score, negative_score, neutral_score)
                    if max_score == positive_score:
                        sentiment = Sentiment.POSITIVE
                    elif max_score == negative_score:
                        sentiment = Sentiment.NEGATIVE
                    else:
                        sentiment = Sentiment.NEUTRAL

                    confidence = max_score

            # Ensure scores are normalized
            total = positive_score + negative_score + neutral_score
            if total > 0:
                positive_score /= total
                negative_score /= total
                neutral_score /= total

            return SentimentAnalysisResult(
                sentiment=sentiment,
                confidence=confidence,
                positive_score=positive_score,
                negative_score=negative_score,
                neutral_score=neutral_score,
                model_used=self.pipeline_config["model_id"],
                raw_scores={
                    "positive": positive_score,
                    "negative": negative_score,
                    "neutral": neutral_score,
                },
            )

        except Exception as e:
            logger.error(f"Error processing sentiment result: {e}")
            return self._create_neutral_result(f"Processing error: {str(e)}")

    def _create_neutral_result(self, reason: str) -> SentimentAnalysisResult:
        """Create a neutral sentiment result for error cases."""
        return SentimentAnalysisResult(
            sentiment=Sentiment.NEUTRAL,
            confidence=0.5,
            positive_score=0.33,
            negative_score=0.33,
            neutral_score=0.34,
            model_used=self.pipeline_config["model_id"],
            raw_scores={"reason": reason},
        )
