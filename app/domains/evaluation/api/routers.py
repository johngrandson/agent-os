"""Evaluation feedback API routers"""

from app.container import Container
from app.domains.evaluation.api.schemas import (
    AccuracyEvalRequest,
    AccuracyEvalResponse,
    EvalFeedbackRequest,
    EvalFeedbackResponse,
)
from app.domains.evaluation.services.accuracy_eval_service import AccuracyEvalService
from app.domains.evaluation.services.eval_feedback_service import EvalFeedbackService
from dependency_injector.wiring import Provide, inject

from fastapi import APIRouter, Depends, HTTPException


eval_feedback_router = APIRouter()
eval_feedback_router.tags = ["Evaluation Feedback"]

accuracy_eval_router = APIRouter()
accuracy_eval_router.tags = ["Accuracy Evaluation"]


@eval_feedback_router.post(
    "",
    response_model=EvalFeedbackResponse,
    status_code=201,
    summary="Process evaluation feedback",
    description="""
    Process a failed evaluation and add feedback to agent knowledge.

    This endpoint:
    1. Fetches evaluation results from AgentOS
    2. Validates that the evaluation failed (score < 8.0)
    3. Publishes an event for async processing
    4. Returns immediately with processing status

    The actual knowledge addition happens asynchronously via event handlers.

    Required fields:
    - eval_id: Evaluation run ID from AgentOS
    - agent_id: Agent ID associated with the evaluation

    Returns:
    Processing status with evaluation details.
    """,
)
@inject
async def process_eval_feedback(
    request: EvalFeedbackRequest,
    eval_feedback_service: EvalFeedbackService = Depends(Provide[Container.eval_feedback_service]),
) -> EvalFeedbackResponse:
    """Process evaluation feedback and queue for knowledge addition"""
    try:
        result = await eval_feedback_service.process_eval_failure(
            eval_id=request.eval_id,
            agent_id=request.agent_id,
        )

        return EvalFeedbackResponse(**result)

    except ValueError as e:
        # Business logic errors (validation failures)
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg) from e
        raise HTTPException(status_code=400, detail=error_msg) from e

    except Exception as e:
        # Infrastructure errors
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process evaluation feedback: {str(e)}",
        ) from e


@accuracy_eval_router.post(
    "",
    response_model=AccuracyEvalResponse,
    status_code=200,
    summary="Run accuracy evaluation with configured agent",
    description="""
    Run accuracy evaluation using the agent's full configuration.

    This endpoint:
    1. Uses the agent from AgnoProvider (with all customizations)
    2. Runs AccuracyEval with the same database as AgentOS
    3. Persists results so they appear in AgentOS
    4. Returns evaluation results

    Advantages over /eval-runs:
    - Uses agent with KnowledgeTools (think, search, analyze)
    - Uses agent with custom instructions
    - Same configuration as webhook/AgentOS agents

    Required fields:
    - name: Evaluation name
    - agent_id: Agent ID to evaluate
    - input: Input text for the agent
    - expected_output: Expected response
    - num_iterations: Number of times to run (1-10)

    Returns:
    Evaluation results with score and status.
    """,
)
@inject
async def run_accuracy_evaluation(
    request: AccuracyEvalRequest,
    accuracy_eval_service: AccuracyEvalService = Depends(Provide[Container.accuracy_eval_service]),
) -> AccuracyEvalResponse:
    """Run accuracy evaluation with configured agent"""
    try:
        result = await accuracy_eval_service.run_accuracy_eval(
            agent_id=request.agent_id,
            eval_name=request.name,
            input_text=request.input,
            expected_output=request.expected_output,
            num_iterations=request.num_iterations,
            additional_guidelines=request.additional_guidelines,
        )

        return AccuracyEvalResponse(**result)

    except ValueError as e:
        # Business logic errors (agent not found, etc.)
        raise HTTPException(status_code=404, detail=str(e)) from e

    except Exception as e:
        # Infrastructure errors
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run evaluation: {str(e)}",
        ) from e
