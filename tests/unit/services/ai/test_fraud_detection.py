"""
Tests for Fraud Detection Service.

Tests business logic and result processing without requiring actual models.
"""

from unittest.mock import Mock, patch

import pytest
from app.services.ai.huggingface.models.result_types import FraudDetectionResult, RiskLevel
from app.services.ai.huggingface.specialized.fraud_detection import FraudDetectionService


class TestFraudDetectionService:
    """Test fraud detection service functionality."""

    @pytest.fixture
    def fraud_service(self):
        """Create fraud detection service instance."""
        return FraudDetectionService()

    def test_service_initialization(self, fraud_service):
        """Test that fraud service initializes correctly."""
        assert fraud_service.model_variant == "default"
        assert fraud_service.pipeline_config["business_task"] == "fraud_detection"
        assert fraud_service.pipeline_config["hf_task"] == "text-classification"

    def test_format_transaction_for_analysis(self, fraud_service):
        """Test transaction data formatting for model input."""
        transaction_data = {
            "amount": 1000.0,
            "merchant": "test_merchant",
            "location": "test_location",
            "card_last_four": "1234",
        }

        result = fraud_service._format_transaction_for_analysis(transaction_data)

        assert "Transaction amount: $1000.00" in result
        assert "Merchant: test_merchant" in result
        assert "Location: test_location" in result
        assert "Card ending: 1234" in result

    def test_format_transaction_high_amount_flag(self, fraud_service):
        """Test that high amounts are flagged appropriately."""
        transaction_data = {"amount": 10000.0}

        result = fraud_service._format_transaction_for_analysis(transaction_data)

        assert "High amount transaction" in result

    def test_format_transaction_suspicious_merchant(self, fraud_service):
        """Test that suspicious merchants are flagged."""
        transaction_data = {"merchant": "crypto_casino_betting"}

        result = fraud_service._format_transaction_for_analysis(transaction_data)

        assert "High-risk merchant category" in result

    def test_format_payment_pattern_single_transaction(self, fraud_service):
        """Test payment pattern formatting with single transaction."""
        payment_history = [{"amount": 100.0}]

        result = fraud_service._format_payment_pattern_for_analysis(payment_history)

        assert "Single transaction, no pattern available" in result

    def test_format_payment_pattern_multiple_transactions(self, fraud_service):
        """Test payment pattern analysis with multiple transactions."""
        payment_history = [
            {"amount": 100.0, "merchant": "store1"},
            {"amount": 200.0, "merchant": "store2"},
            {"amount": 150.0, "merchant": "store1"},
        ]

        result = fraud_service._format_payment_pattern_for_analysis(payment_history)

        assert "Pattern analysis: 3 transactions" in result
        assert "Average amount: $150.00" in result
        assert "Amount range: $100.00 to $200.00" in result
        assert "Unique merchants: 2" in result

    def test_process_fraud_result_high_risk(self, fraud_service):
        """Test processing of high-risk fraud result."""
        # Mock high fraud score result
        raw_result = [[{"label": "FRAUD", "score": 0.9}]]
        context = {"amount": 5000.0, "merchant": "suspicious_shop"}

        result = fraud_service._process_fraud_result(raw_result, context)

        assert isinstance(result, FraudDetectionResult)
        assert result.is_fraudulent is True
        assert result.risk_level == RiskLevel.CRITICAL
        assert result.risk_score == 0.9
        assert "High AI model confidence for fraud" in result.risk_factors

    def test_process_fraud_result_low_risk(self, fraud_service):
        """Test processing of low-risk fraud result."""
        # Mock low fraud score result
        raw_result = [[{"label": "LEGITIMATE", "score": 0.1}]]
        context = {"amount": 50.0, "merchant": "grocery_store"}

        result = fraud_service._process_fraud_result(raw_result, context)

        assert isinstance(result, FraudDetectionResult)
        assert result.is_fraudulent is False
        assert result.risk_level == RiskLevel.LOW
        assert result.risk_score == 0.1

    def test_process_fraud_result_error_handling(self, fraud_service):
        """Test error handling in result processing."""
        # Invalid result format
        raw_result = "invalid_format"
        context = {}

        result = fraud_service._process_fraud_result(raw_result, context)

        assert isinstance(result, FraudDetectionResult)
        assert result.is_fraudulent is False
        assert result.risk_level == RiskLevel.MEDIUM  # Default fallback for invalid format
        assert result.risk_score == 0.5  # Default moderate risk
        assert "General risk indicators present" in result.risk_factors

    def test_identify_risk_factors(self, fraud_service):
        """Test risk factor identification."""
        context = {"amount": 15000.0, "merchant": "crypto_exchange"}

        factors = fraud_service._identify_risk_factors(context, 0.8)

        assert "High AI model confidence for fraud" in factors
        assert "Very high transaction amount" in factors

    @patch.object(FraudDetectionService, "get_pipeline")
    @patch.object(FraudDetectionService, "_run_pipeline")
    async def test_analyze_transaction(self, mock_run_pipeline, mock_get_pipeline, fraud_service):
        """Test transaction analysis workflow."""
        # Setup mocks
        mock_pipeline = Mock()
        mock_get_pipeline.return_value = mock_pipeline

        mock_result = [[{"label": "FRAUD", "score": 0.7}]]
        mock_run_pipeline.return_value = mock_result

        transaction_data = {"amount": 1000.0, "merchant": "test_merchant"}

        # Execute test
        result = await fraud_service.analyze_transaction(transaction_data)

        # Verify behavior
        assert isinstance(result, FraudDetectionResult)
        assert result.is_fraudulent is True
        assert result.risk_level == RiskLevel.HIGH

        mock_get_pipeline.assert_called_once()
        mock_run_pipeline.assert_called_once()

    @patch.object(FraudDetectionService, "get_pipeline")
    @patch.object(FraudDetectionService, "_run_pipeline")
    async def test_check_merchant_risk(self, mock_run_pipeline, mock_get_pipeline, fraud_service):
        """Test merchant risk checking."""
        # Setup mocks
        mock_pipeline = Mock()
        mock_get_pipeline.return_value = mock_pipeline

        mock_result = [[{"label": "SAFE", "score": 0.2}]]
        mock_run_pipeline.return_value = mock_result

        # Execute test
        result = await fraud_service.check_merchant_risk("trusted_store", 100.0)

        # Verify behavior
        assert isinstance(result, FraudDetectionResult)
        assert result.is_fraudulent is False
        assert result.risk_level == RiskLevel.LOW

    async def test_analyze_payment_pattern_empty_history(self, fraud_service):
        """Test payment pattern analysis with empty history."""
        result = await fraud_service.analyze_payment_pattern([])

        assert isinstance(result, FraudDetectionResult)
        assert result.is_fraudulent is False
        assert result.risk_level == RiskLevel.LOW
        assert "No payment history to analyze" in result.risk_factors
