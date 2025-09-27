"""
Content Moderation Service using HuggingFace models.

Specialized service for moderating user-generated content, detecting toxic
language, inappropriate content, and ensuring platform safety.
"""

from typing import Any

from core.logger import get_module_logger

from ..huggingface_service import HuggingFaceService
from ..models.pipeline_factory import PipelineFactory
from ..models.result_types import ContentModerationResult, SafetyLevel


logger = get_module_logger(__name__)


class ContentModerationService(HuggingFaceService):
    """
    Service for moderating user-generated content.

    Focuses on platform safety - detecting toxic content, inappropriate
    language, and content that violates community guidelines.
    """

    def __init__(self, model_variant: str = "default"):
        super().__init__()
        self.model_variant = model_variant
        self.pipeline_config = PipelineFactory.create_pipeline_config(
            "content_moderation", model_variant
        )

        # Define content categories we monitor
        self.moderation_categories = [
            "toxic",
            "severe_toxic",
            "obscene",
            "threat",
            "insult",
            "identity_hate",
            "harassment",
            "spam",
        ]

    async def moderate_content(self, content: str) -> ContentModerationResult:
        """
        Moderate user-generated content for safety and appropriateness.

        Args:
            content: Text content to moderate

        Returns:
            ContentModerationResult with safety assessment

        Example:
            result = await moderation_service.moderate_content("user post content")
            if not result.is_safe:
                print(f"Content flagged: {result.flagged_categories}")
        """
        logger.info("Moderating content for safety")

        if not content or not content.strip():
            return self._create_safe_result("Empty content")

        # Get moderation pipeline
        pipeline = await self.get_pipeline(
            self.pipeline_config["hf_task"], self.pipeline_config["model_id"]
        )

        # Run content moderation
        result = await self._run_pipeline(pipeline, content.strip())

        return self._process_moderation_result(result, content)

    async def check_toxicity(self, text: str) -> ContentModerationResult:
        """
        Specifically check for toxic language and harmful content.

        Args:
            text: Text to check for toxicity

        Returns:
            ContentModerationResult focused on toxicity assessment
        """
        logger.info("Checking content for toxicity")

        result = await self.moderate_content(text)

        # Focus result on toxicity aspects
        toxicity_categories = [
            cat
            for cat in result.flagged_categories
            if "toxic" in cat.lower() or "threat" in cat.lower()
        ]

        return ContentModerationResult(
            is_safe=result.is_safe,
            safety_level=result.safety_level,
            confidence=result.confidence,
            flagged_categories=toxicity_categories,
            toxicity_score=result.toxicity_score,
            model_used=result.model_used,
            raw_scores=result.raw_scores,
        )

    async def moderate_user_post(
        self, post_content: str, user_context: dict | None = None
    ) -> ContentModerationResult:
        """
        Moderate a user post with additional context.

        Args:
            post_content: The post content to moderate
            user_context: Optional user context (history, reputation, etc.)

        Returns:
            ContentModerationResult with post-specific assessment
        """
        logger.info("Moderating user post content")

        result = await self.moderate_content(post_content)

        # Adjust assessment based on user context
        if user_context:
            result = self._adjust_for_user_context(result, user_context)

        return result

    async def moderate_comment(
        self, comment: str, parent_context: str | None = None
    ) -> ContentModerationResult:
        """
        Moderate a comment, optionally considering parent post context.

        Args:
            comment: Comment content to moderate
            parent_context: Optional parent post content for context

        Returns:
            ContentModerationResult for the comment
        """
        logger.info("Moderating comment content")

        # Combine comment with parent context if available
        if parent_context:
            full_context = f"Parent: {parent_context[:200]}... Comment: {comment}"
        else:
            full_context = comment

        return await self.moderate_content(full_context)

    async def batch_moderate(self, contents: list[str]) -> list[ContentModerationResult]:
        """
        Moderate multiple pieces of content efficiently.

        Args:
            contents: List of content to moderate

        Returns:
            List of ContentModerationResult in same order as input
        """
        logger.info(f"Batch moderating {len(contents)} pieces of content")

        results = []
        for content in contents:
            try:
                result = await self.moderate_content(content)
                results.append(result)
            except Exception as e:
                logger.error(f"Error moderating content: {e}")
                results.append(self._create_safe_result(f"Moderation error: {str(e)}"))

        return results

    async def get_content_safety_score(self, content: str) -> float:
        """
        Get a simple safety score (0.0 to 1.0) for content.

        Args:
            content: Content to assess

        Returns:
            Safety score between 0.0 (unsafe) and 1.0 (safe)
        """
        result = await self.moderate_content(content)
        return 1.0 - result.toxicity_score

    def _adjust_for_user_context(
        self, result: ContentModerationResult, user_context: dict
    ) -> ContentModerationResult:
        """Adjust moderation result based on user context."""
        # If user has good reputation, be slightly more lenient
        if user_context.get("reputation", 0) > 0.8:
            if result.safety_level == SafetyLevel.QUESTIONABLE:
                result.confidence *= 0.9  # Slightly less confident in flagging

        # If user has history of violations, be more strict
        elif user_context.get("violation_history", 0) > 3:
            if result.safety_level == SafetyLevel.QUESTIONABLE:
                result.safety_level = SafetyLevel.UNSAFE
                result.flagged_categories.append("repeat_offender_pattern")

        return result

    def _process_moderation_result(
        self, raw_result: Any, original_content: str
    ) -> ContentModerationResult:
        """Process raw model result into structured ContentModerationResult."""
        try:
            toxicity_score = 0.0
            flagged_categories = []
            confidence = 0.0
            safety_level = SafetyLevel.SAFE

            if isinstance(raw_result, list) and raw_result:
                # Process classification results
                if isinstance(raw_result[0], dict):
                    # Single prediction format
                    result_item = raw_result[0]
                    label = result_item.get("label", "").lower()
                    score = result_item.get("score", 0.0)

                    if any(toxic_word in label for toxic_word in ["toxic", "negative", "harmful"]):
                        toxicity_score = score
                        if score > 0.7:
                            flagged_categories.append("toxic_content")

                    confidence = score

                elif isinstance(raw_result, list):
                    # Multiple predictions format
                    max_toxic_score = 0.0

                    for item in raw_result:
                        if isinstance(item, dict):
                            label = item.get("label", "").lower()
                            score = item.get("score", 0.0)

                            # Check for various toxic categories
                            if "toxic" in label:
                                max_toxic_score = max(max_toxic_score, score)
                                if score > 0.5:
                                    flagged_categories.append("toxic")
                            elif "threat" in label and score > 0.5:
                                flagged_categories.append("threat")
                            elif "insult" in label and score > 0.5:
                                flagged_categories.append("insult")
                            elif "obscene" in label and score > 0.5:
                                flagged_categories.append("obscene")
                            elif "hate" in label and score > 0.5:
                                flagged_categories.append("hate_speech")

                    toxicity_score = max_toxic_score
                    confidence = max_toxic_score

            # Determine safety level and overall safety
            if toxicity_score >= 0.8:
                safety_level = SafetyLevel.TOXIC
                is_safe = False
            elif toxicity_score >= 0.6:
                safety_level = SafetyLevel.UNSAFE
                is_safe = False
            elif toxicity_score >= 0.4:
                safety_level = SafetyLevel.QUESTIONABLE
                is_safe = False
            else:
                safety_level = SafetyLevel.SAFE
                is_safe = True

            # Add basic content analysis flags
            if not flagged_categories:
                flagged_categories = self._analyze_content_patterns(original_content)

            return ContentModerationResult(
                is_safe=is_safe,
                safety_level=safety_level,
                confidence=confidence,
                flagged_categories=flagged_categories,
                toxicity_score=toxicity_score,
                model_used=self.pipeline_config["model_id"],
                raw_scores={"toxicity_score": toxicity_score},
            )

        except Exception as e:
            logger.error(f"Error processing moderation result: {e}")
            return self._create_safe_result(f"Processing error: {str(e)}")

    def _analyze_content_patterns(self, content: str) -> list[str]:
        """Analyze content for basic patterns that might indicate issues."""
        patterns = []
        content_lower = content.lower()

        # Check for excessive caps (shouting)
        if len([c for c in content if c.isupper()]) > len(content) * 0.7:
            patterns.append("excessive_caps")

        # Check for repeated characters/words
        words = content_lower.split()
        if len(words) != len(set(words)) and len(words) > 5:
            patterns.append("repetitive_content")

        # Check for potential spam patterns
        if any(
            spam_word in content_lower for spam_word in ["click here", "buy now", "limited time"]
        ):
            patterns.append("potential_spam")

        return patterns

    def _create_safe_result(self, reason: str) -> ContentModerationResult:
        """Create a safe moderation result for edge cases."""
        return ContentModerationResult(
            is_safe=True,
            safety_level=SafetyLevel.SAFE,
            confidence=1.0,
            flagged_categories=[],
            toxicity_score=0.0,
            model_used=self.pipeline_config["model_id"],
            raw_scores={"reason": reason},
        )
