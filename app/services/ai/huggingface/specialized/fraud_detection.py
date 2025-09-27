"""
Fraud Detection Service using HuggingFace models.

Specialized service for analyzing payment patterns, transaction data,
and detecting potentially fraudulent activities.
"""

from typing import Any

from core.logger import get_module_logger

from ..huggingface_service import HuggingFaceService
from ..models.pipeline_factory import PipelineFactory
from ..models.result_types import FraudDetectionResult, RiskLevel


logger = get_module_logger(__name__)


class FraudDetectionService(HuggingFaceService):
    """
    Service for detecting fraudulent transactions and payment patterns.

    Uses AI models to analyze transaction data and identify potential fraud.
    Focused on real business value - protecting against financial losses.
    """

    def __init__(self, model_variant: str = "default"):
        super().__init__()
        self.model_variant = model_variant
        self.pipeline_config = PipelineFactory.create_pipeline_config(
            "fraud_detection", model_variant
        )

    async def analyze_transaction(self, transaction_data: dict[str, Any]) -> FraudDetectionResult:
        """
        Analyze a single transaction for fraud indicators.

        Args:
            transaction_data: Transaction details including amount, merchant, etc.

        Returns:
            FraudDetectionResult with risk assessment

        Example:
            result = await fraud_service.analyze_transaction({
                "amount": 1000.0,
                "merchant": "suspicious_shop",
                "card_last_four": "1234",
                "location": "unusual_location"
            })
        """
        logger.info("Analyzing transaction for fraud indicators")

        # Convert transaction data to text for model analysis
        transaction_text = self._format_transaction_for_analysis(transaction_data)

        # Get model pipeline
        pipeline = await self.get_pipeline(
            self.pipeline_config["hf_task"], self.pipeline_config["model_id"]
        )

        # Run analysis
        result = await self._run_pipeline(pipeline, transaction_text)

        # Process and return structured result
        return self._process_fraud_result(result, transaction_data)

    async def analyze_payment_pattern(
        self, payment_history: list[dict[str, Any]]
    ) -> FraudDetectionResult:
        """
        Analyze a series of payments for suspicious patterns.

        Args:
            payment_history: List of payment transactions

        Returns:
            FraudDetectionResult for the payment pattern
        """
        logger.info(f"Analyzing payment pattern with {len(payment_history)} transactions")

        if not payment_history:
            return FraudDetectionResult(
                is_fraudulent=False,
                risk_level=RiskLevel.LOW,
                confidence=1.0,
                risk_score=0.0,
                risk_factors=["No payment history to analyze"],
                model_used=self.pipeline_config["model_id"],
            )

        # Analyze pattern characteristics
        pattern_text = self._format_payment_pattern_for_analysis(payment_history)

        pipeline = await self.get_pipeline(
            self.pipeline_config["hf_task"], self.pipeline_config["model_id"]
        )

        result = await self._run_pipeline(pipeline, pattern_text)

        return self._process_fraud_result(result, {"pattern_analysis": True})

    async def check_merchant_risk(
        self, merchant_name: str, transaction_amount: float
    ) -> FraudDetectionResult:
        """
        Check risk level for a specific merchant and transaction amount.

        Args:
            merchant_name: Name of the merchant
            transaction_amount: Transaction amount

        Returns:
            FraudDetectionResult for merchant risk
        """
        logger.info(f"Checking merchant risk: {merchant_name}")

        merchant_text = f"Transaction of ${transaction_amount:.2f} at merchant: {merchant_name}"

        pipeline = await self.get_pipeline(
            self.pipeline_config["hf_task"], self.pipeline_config["model_id"]
        )

        result = await self._run_pipeline(pipeline, merchant_text)

        return self._process_fraud_result(
            result, {"merchant": merchant_name, "amount": transaction_amount}
        )

    def _format_transaction_for_analysis(self, transaction_data: dict[str, Any]) -> str:
        """Format transaction data for model analysis."""
        parts = []

        if "amount" in transaction_data:
            amount = transaction_data["amount"]
            parts.append(f"Transaction amount: ${amount:.2f}")

            # Flag unusual amounts
            if amount > 5000:
                parts.append("High amount transaction")
            elif amount < 1:
                parts.append("Micro transaction")

        if "merchant" in transaction_data:
            merchant = transaction_data["merchant"]
            parts.append(f"Merchant: {merchant}")

            # Flag suspicious merchant names
            suspicious_keywords = ["casino", "betting", "gambling", "crypto", "bitcoin"]
            if any(keyword in merchant.lower() for keyword in suspicious_keywords):
                parts.append("High-risk merchant category")

        if "location" in transaction_data:
            parts.append(f"Location: {transaction_data['location']}")

        if "time" in transaction_data:
            parts.append(f"Time: {transaction_data['time']}")

        if "card_last_four" in transaction_data:
            parts.append(f"Card ending: {transaction_data['card_last_four']}")

        return " | ".join(parts)

    def _format_payment_pattern_for_analysis(self, payment_history: list[dict[str, Any]]) -> str:
        """Format payment pattern for model analysis."""
        if len(payment_history) <= 1:
            return "Single transaction, no pattern available"

        # Analyze amounts
        amounts = [p.get("amount", 0) for p in payment_history]
        avg_amount = sum(amounts) / len(amounts)
        max_amount = max(amounts)
        min_amount = min(amounts)

        # Analyze merchants
        merchants = [p.get("merchant", "unknown") for p in payment_history]
        unique_merchants = len(set(merchants))

        # Analyze timing
        pattern_parts = [
            f"Pattern analysis: {len(payment_history)} transactions",
            f"Average amount: ${avg_amount:.2f}",
            f"Amount range: ${min_amount:.2f} to ${max_amount:.2f}",
            f"Unique merchants: {unique_merchants}",
        ]

        # Flag suspicious patterns
        if len(payment_history) > 10 and max_amount > avg_amount * 5:
            pattern_parts.append("Unusual spike in transaction amount")

        if unique_merchants == 1 and len(payment_history) > 5:
            pattern_parts.append("Repeated transactions to same merchant")

        return " | ".join(pattern_parts)

    def _process_fraud_result(
        self, raw_result: Any, context: dict[str, Any]
    ) -> FraudDetectionResult:
        """Process raw model result into structured FraudDetectionResult."""
        try:
            # Handle different model output formats
            if isinstance(raw_result, list) and raw_result:
                # Handle nested list structure [[{...}]]
                if isinstance(raw_result[0], list) and raw_result[0]:
                    first_item = raw_result[0][0]
                    if isinstance(first_item, dict):
                        fraud_score = first_item.get("score", 0.0)
                    else:
                        fraud_score = (
                            float(first_item) if isinstance(first_item, (int, float)) else 0.0
                        )
                elif isinstance(raw_result[0], dict):
                    # Direct list of dicts
                    fraud_score = 0.0
                    for item in raw_result:
                        if "fraud" in item.get("label", "").lower():
                            fraud_score = item.get("score", 0.0)
                            break

                    # If no explicit fraud label, use first score as risk indicator
                    if fraud_score == 0.0:
                        fraud_score = raw_result[0].get("score", 0.0)
                else:
                    # Simple list format
                    fraud_score = (
                        float(raw_result[0]) if isinstance(raw_result[0], (int, float)) else 0.0
                    )
            else:
                # Single value or other format
                fraud_score = 0.5  # Default moderate risk

            # Determine risk level and fraud status
            if fraud_score >= 0.8:
                risk_level = RiskLevel.CRITICAL
                is_fraudulent = True
            elif fraud_score >= 0.6:
                risk_level = RiskLevel.HIGH
                is_fraudulent = True
            elif fraud_score >= 0.4:
                risk_level = RiskLevel.MEDIUM
                is_fraudulent = False
            else:
                risk_level = RiskLevel.LOW
                is_fraudulent = False

            # Generate risk factors based on context
            risk_factors = self._identify_risk_factors(context, fraud_score)

            return FraudDetectionResult(
                is_fraudulent=is_fraudulent,
                risk_level=risk_level,
                confidence=min(fraud_score * 1.2, 1.0),  # Boost confidence slightly
                risk_score=fraud_score,
                risk_factors=risk_factors,
                model_used=self.pipeline_config["model_id"],
                raw_scores={"fraud_score": fraud_score},
            )

        except Exception as e:
            logger.error(f"Error processing fraud detection result: {e}")
            # Return safe default
            return FraudDetectionResult(
                is_fraudulent=False,
                risk_level=RiskLevel.LOW,
                confidence=0.5,
                risk_score=0.0,
                risk_factors=["Error in analysis"],
                model_used=self.pipeline_config["model_id"],
            )

    def _identify_risk_factors(self, context: dict[str, Any], risk_score: float) -> list[str]:
        """Identify specific risk factors based on context and score."""
        factors = []

        if risk_score > 0.7:
            factors.append("High AI model confidence for fraud")

        if "amount" in context:
            amount = context["amount"]
            if amount > 10000:
                factors.append("Very high transaction amount")
            elif amount > 5000:
                factors.append("High transaction amount")

        if "merchant" in context:
            merchant = context["merchant"]
            if any(word in merchant.lower() for word in ["casino", "betting", "crypto"]):
                factors.append("High-risk merchant category")

        if "pattern_analysis" in context:
            factors.append("Suspicious payment pattern detected")

        if not factors:
            factors.append("General risk indicators present")

        return factors
