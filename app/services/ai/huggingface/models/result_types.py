"""
Result data classes for AI services.

Standardized result types for different AI tasks. Makes service responses
consistent and easy to work with across the application.
"""

from dataclasses import dataclass
from enum import Enum


class RiskLevel(Enum):
    """Risk levels for fraud detection and security tasks."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Sentiment(Enum):
    """Sentiment categories."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class SafetyLevel(Enum):
    """Content safety levels."""

    SAFE = "safe"
    QUESTIONABLE = "questionable"
    UNSAFE = "unsafe"
    TOXIC = "toxic"


@dataclass
class FraudDetectionResult:
    """Result from fraud detection analysis."""

    is_fraudulent: bool
    risk_level: RiskLevel
    confidence: float
    risk_score: float  # 0.0 to 1.0
    risk_factors: list[str]
    model_used: str
    raw_scores: dict[str, float] | None = None

    @property
    def is_high_risk(self) -> bool:
        """Check if transaction is high risk (HIGH or CRITICAL)."""
        return self.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]


@dataclass
class SentimentAnalysisResult:
    """Result from sentiment analysis."""

    sentiment: Sentiment
    confidence: float
    positive_score: float
    negative_score: float
    neutral_score: float
    model_used: str
    raw_scores: dict[str, float] | None = None

    @property
    def is_positive(self) -> bool:
        """Check if sentiment is positive."""
        return self.sentiment == Sentiment.POSITIVE

    @property
    def is_negative(self) -> bool:
        """Check if sentiment is negative."""
        return self.sentiment == Sentiment.NEGATIVE

    @property
    def overall_score(self) -> float:
        """Overall sentiment score (-1.0 to 1.0, negative to positive)."""
        return self.positive_score - self.negative_score


@dataclass
class ContentModerationResult:
    """Result from content moderation analysis."""

    is_safe: bool
    safety_level: SafetyLevel
    confidence: float
    flagged_categories: list[str]
    toxicity_score: float  # 0.0 to 1.0
    model_used: str
    raw_scores: dict[str, float] | None = None

    @property
    def needs_human_review(self) -> bool:
        """Check if content needs human review."""
        return self.safety_level == SafetyLevel.QUESTIONABLE or self.confidence < 0.8


@dataclass
class TextClassificationResult:
    """Result from generic text classification."""

    predicted_label: str
    confidence: float
    all_scores: dict[str, float]
    model_used: str
    raw_scores: dict[str, float] | None = None

    @property
    def top_predictions(self, limit: int = 3) -> list[tuple[str, float]]:
        """Get top predictions sorted by confidence."""
        sorted_scores = sorted(self.all_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:limit]
