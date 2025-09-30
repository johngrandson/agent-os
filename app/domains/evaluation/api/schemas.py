"""Evaluation API schemas"""

from pydantic import BaseModel, Field


class EvalFeedbackRequest(BaseModel):
    """Request to process evaluation feedback"""

    eval_id: str = Field(..., description="Evaluation run ID from AgentOS")
    agent_id: str = Field(..., description="Agent ID associated with the evaluation")


class EvalFeedbackResponse(BaseModel):
    """Response for evaluation feedback processing"""

    eval_id: str = Field(..., description="Evaluation run ID")
    agent_id: str = Field(..., description="Agent ID")
    score: float = Field(..., description="Evaluation score")
    feedback_added: bool = Field(..., description="Whether feedback was added to knowledge")
    message: str = Field(..., description="Status message")


class AccuracyEvalRequest(BaseModel):
    """Request to run accuracy evaluation using configured agent"""

    name: str = Field(..., description="Name for this evaluation run")
    agent_id: str = Field(..., description="Agent ID to evaluate")
    input: str = Field(..., description="Input text for the agent")
    expected_output: str = Field(..., description="Expected output from the agent")
    num_iterations: int = Field(
        default=1, ge=1, le=10, description="Number of times to run evaluation"
    )
    additional_guidelines: str | None = Field(
        None, description="Additional guidelines for evaluation"
    )


class AccuracyEvalResponse(BaseModel):
    """Response from accuracy evaluation"""

    eval_id: str = Field(..., description="Evaluation run ID")
    agent_id: str = Field(..., description="Agent ID that was evaluated")
    name: str = Field(..., description="Evaluation name")
    avg_score: float = Field(..., description="Average score across iterations")
    num_iterations: int = Field(..., description="Number of iterations run")
    status: str = Field(..., description="Evaluation status (passed/failed)")
    message: str = Field(..., description="Result message")
