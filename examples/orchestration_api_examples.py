"""
Examples of using the Orchestration API

This file demonstrates how to use the orchestration API endpoints
to create, execute, and monitor multi-agent workflows.
"""

import json
import time
import asyncio
import httpx
from typing import Dict, Any


class OrchestrationAPIClient:
    """Simple client for interacting with the Orchestration API"""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    # Workflow Management Methods

    async def create_workflow(self, workflow_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new workflow definition"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/orchestration/workflows",
            json={"workflow_definition": workflow_definition}
        )
        response.raise_for_status()
        return response.json()

    async def execute_workflow(self, workflow_id: str, workflow_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a workflow"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/orchestration/workflows/{workflow_id}/execute",
            json={"workflow_definition": workflow_definition}
        )
        response.raise_for_status()
        return response.json()

    async def validate_workflow(self, workflow_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a workflow definition"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/orchestration/validate",
            json={"workflow_definition": workflow_definition}
        )
        response.raise_for_status()
        return response.json()

    # Execution Management Methods

    async def get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """Get workflow execution status"""
        response = await self.client.get(
            f"{self.base_url}/api/v1/orchestration/executions/{execution_id}"
        )
        response.raise_for_status()
        return response.json()

    async def cancel_execution(self, execution_id: str) -> None:
        """Cancel a workflow execution"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/orchestration/executions/{execution_id}/cancel"
        )
        response.raise_for_status()

    async def get_execution_tasks(self, execution_id: str, status: str = None) -> list:
        """Get tasks for a workflow execution"""
        params = {}
        if status:
            params["status"] = status

        response = await self.client.get(
            f"{self.base_url}/api/v1/orchestration/executions/{execution_id}/tasks",
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def retry_task(self, execution_id: str, task_id: str) -> Dict[str, Any]:
        """Retry a failed task"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/orchestration/executions/{execution_id}/tasks/{task_id}/retry"
        )
        response.raise_for_status()
        return response.json()

    # Monitoring Methods

    async def get_health_status(self) -> Dict[str, Any]:
        """Get orchestration system health"""
        response = await self.client.get(
            f"{self.base_url}/api/v1/orchestration/health"
        )
        response.raise_for_status()
        return response.json()

    async def list_executions(self, status: str = None, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """List workflow executions"""
        params = {"limit": limit, "offset": offset}
        if status:
            params["status"] = status

        response = await self.client.get(
            f"{self.base_url}/api/v1/orchestration/executions",
            params=params
        )
        response.raise_for_status()
        return response.json()

    async def cleanup_old_executions(self, max_age_hours: int = 24) -> Dict[str, Any]:
        """Cleanup old workflow executions"""
        response = await self.client.delete(
            f"{self.base_url}/api/v1/orchestration/cleanup",
            params={"max_age_hours": max_age_hours}
        )
        response.raise_for_status()
        return response.json()


# Example Workflow Definitions

def create_simple_sequential_workflow() -> Dict[str, Any]:
    """
    Create a simple sequential workflow: Data Collection → Processing → Validation
    """
    return {
        "workflow_id": "simple-sequential-001",
        "name": "Simple Sequential Data Processing",
        "description": "Collect data, process it, then validate the results",
        "tasks": [
            {
                "task_id": "collect_data",
                "task_type": "data_collection",
                "agent_id": "data-collector-agent",
                "depends_on": [],
                "data": {
                    "source": "database",
                    "query": "SELECT * FROM raw_data WHERE status='pending'",
                    "limit": 1000
                },
                "timeout_seconds": 300,
                "max_retries": 2
            },
            {
                "task_id": "process_data",
                "task_type": "data_processing",
                "agent_id": "data-processor-agent",
                "depends_on": ["collect_data"],
                "data": {
                    "processing_type": "normalization",
                    "output_format": "json",
                    "apply_filters": True
                },
                "timeout_seconds": 600,
                "max_retries": 3
            },
            {
                "task_id": "validate_data",
                "task_type": "data_validation",
                "agent_id": "data-validator-agent",
                "depends_on": ["process_data"],
                "data": {
                    "validation_rules": [
                        "not_null",
                        "format_check",
                        "business_rules"
                    ],
                    "fail_on_error": True
                },
                "timeout_seconds": 180,
                "max_retries": 1
            }
        ],
        "global_timeout_seconds": 1800,  # 30 minutes
        "retry_policy": {
            "max_retries": 3,
            "backoff_seconds": 5
        },
        "metadata": {
            "created_by": "data_team",
            "priority": "high",
            "environment": "production"
        }
    }


def create_parallel_workflow() -> Dict[str, Any]:
    """
    Create a parallel workflow: Multiple data sources processed simultaneously
    """
    return {
        "workflow_id": "parallel-processing-001",
        "name": "Parallel Data Source Processing",
        "description": "Process multiple data sources in parallel, then merge results",
        "tasks": [
            {
                "task_id": "process_source_a",
                "task_type": "data_processing",
                "agent_id": "source-a-processor",
                "depends_on": [],
                "data": {
                    "source": "api_endpoint_a",
                    "format": "json"
                },
                "timeout_seconds": 300
            },
            {
                "task_id": "process_source_b",
                "task_type": "data_processing",
                "agent_id": "source-b-processor",
                "depends_on": [],
                "data": {
                    "source": "database_b",
                    "format": "csv"
                },
                "timeout_seconds": 300
            },
            {
                "task_id": "process_source_c",
                "task_type": "data_processing",
                "agent_id": "source-c-processor",
                "depends_on": [],
                "data": {
                    "source": "file_system_c",
                    "format": "xml"
                },
                "timeout_seconds": 300
            },
            {
                "task_id": "merge_results",
                "task_type": "data_aggregation",
                "agent_id": "data-merger-agent",
                "depends_on": ["process_source_a", "process_source_b", "process_source_c"],
                "data": {
                    "merge_strategy": "union",
                    "deduplicate": True,
                    "output_format": "parquet"
                },
                "timeout_seconds": 600
            },
            {
                "task_id": "generate_report",
                "task_type": "report_generation",
                "agent_id": "report-generator-agent",
                "depends_on": ["merge_results"],
                "data": {
                    "report_type": "summary",
                    "include_charts": True,
                    "format": "pdf"
                },
                "timeout_seconds": 180
            }
        ],
        "global_timeout_seconds": 2400,  # 40 minutes
        "metadata": {
            "created_by": "analytics_team",
            "department": "marketing"
        }
    }


def create_conditional_workflow() -> Dict[str, Any]:
    """
    Create a workflow with conditional execution
    """
    return {
        "workflow_id": "conditional-processing-001",
        "name": "Conditional Data Processing",
        "description": "Process data with conditional branching based on data quality",
        "tasks": [
            {
                "task_id": "data_quality_check",
                "task_type": "quality_assessment",
                "agent_id": "quality-checker-agent",
                "depends_on": [],
                "data": {
                    "quality_threshold": 0.8,
                    "check_completeness": True,
                    "check_accuracy": True
                },
                "timeout_seconds": 120
            },
            {
                "task_id": "standard_processing",
                "task_type": "data_processing",
                "agent_id": "standard-processor-agent",
                "depends_on": ["data_quality_check"],
                "data": {
                    "processing_level": "standard"
                },
                "conditions": {
                    "execute_if": {
                        "task": "data_quality_check",
                        "result_field": "quality_score",
                        "operator": ">=",
                        "value": 0.8
                    }
                },
                "timeout_seconds": 300
            },
            {
                "task_id": "enhanced_processing",
                "task_type": "data_processing",
                "agent_id": "enhanced-processor-agent",
                "depends_on": ["data_quality_check"],
                "data": {
                    "processing_level": "enhanced",
                    "apply_ml_models": True,
                    "quality_improvement": True
                },
                "conditions": {
                    "execute_if": {
                        "task": "data_quality_check",
                        "result_field": "quality_score",
                        "operator": "<",
                        "value": 0.8
                    }
                },
                "timeout_seconds": 900
            }
        ],
        "global_timeout_seconds": 1800,
        "metadata": {
            "workflow_type": "conditional",
            "quality_driven": True
        }
    }


# Usage Examples

async def example_1_simple_workflow_execution():
    """
    Example 1: Create and execute a simple workflow
    """
    print("Example 1: Simple Sequential Workflow")
    print("=====================================")

    async with OrchestrationAPIClient() as client:
        # Create workflow definition
        workflow_def = create_simple_sequential_workflow()
        print(f"Creating workflow: {workflow_def['name']}")

        # Validate workflow first
        print("Validating workflow...")
        validation = await client.validate_workflow(workflow_def)
        if not validation["is_valid"]:
            print(f"Validation failed: {validation['errors']}")
            return

        print("✓ Workflow validation passed")

        # Create workflow
        create_result = await client.create_workflow(workflow_def)
        print(f"✓ Workflow created: {create_result['workflow_id']}")

        # Execute workflow
        print("Starting workflow execution...")
        execution = await client.execute_workflow(
            workflow_def["workflow_id"],
            workflow_def
        )
        execution_id = execution["execution_id"]
        print(f"✓ Execution started: {execution_id}")

        # Monitor execution
        print("Monitoring execution...")
        for i in range(10):  # Check for up to 10 iterations
            status = await client.get_execution_status(execution_id)
            print(f"Status: {status['status']}")

            if status["status"] in ["completed", "failed", "cancelled"]:
                break

            await asyncio.sleep(2)  # Wait 2 seconds between checks

        # Get final results
        final_status = await client.get_execution_status(execution_id)
        print(f"Final status: {final_status['status']}")

        # Get task details
        tasks = await client.get_execution_tasks(execution_id)
        print(f"Tasks executed: {len(tasks)}")
        for task in tasks:
            print(f"  - {task['workflow_task_id']}: {task['status']}")


async def example_2_parallel_workflow_with_monitoring():
    """
    Example 2: Execute parallel workflow with detailed monitoring
    """
    print("\nExample 2: Parallel Workflow with Monitoring")
    print("============================================")

    async with OrchestrationAPIClient() as client:
        workflow_def = create_parallel_workflow()
        print(f"Executing parallel workflow: {workflow_def['name']}")

        # Create and execute
        await client.create_workflow(workflow_def)
        execution = await client.execute_workflow(
            workflow_def["workflow_id"],
            workflow_def
        )
        execution_id = execution["execution_id"]

        print(f"Execution ID: {execution_id}")

        # Monitor with detailed task status
        while True:
            status = await client.get_execution_status(execution_id)
            tasks = await client.get_execution_tasks(execution_id)

            print(f"\nExecution Status: {status['status']}")
            print("Task Progress:")

            task_summary = {}
            for task in tasks:
                task_status = task["status"]
                task_summary[task_status] = task_summary.get(task_status, 0) + 1
                print(f"  {task['workflow_task_id']}: {task_status}")

            print(f"Summary: {dict(task_summary)}")

            if status["status"] in ["completed", "failed", "cancelled"]:
                break

            await asyncio.sleep(3)

        print(f"\nWorkflow completed with status: {status['status']}")


async def example_3_error_handling_and_retry():
    """
    Example 3: Demonstrate error handling and task retry
    """
    print("\nExample 3: Error Handling and Task Retry")
    print("=======================================")

    async with OrchestrationAPIClient() as client:
        workflow_def = create_simple_sequential_workflow()

        # Execute workflow
        await client.create_workflow(workflow_def)
        execution = await client.execute_workflow(
            workflow_def["workflow_id"],
            workflow_def
        )
        execution_id = execution["execution_id"]

        # Monitor for failed tasks
        while True:
            status = await client.get_execution_status(execution_id)
            failed_tasks = await client.get_execution_tasks(execution_id, status="failed")

            if failed_tasks:
                print(f"Found {len(failed_tasks)} failed tasks")
                for task in failed_tasks:
                    print(f"Retrying failed task: {task['workflow_task_id']}")
                    try:
                        retry_result = await client.retry_task(execution_id, task["workflow_task_id"])
                        print(f"✓ Task retry initiated: {retry_result['retry_count']}")
                    except Exception as e:
                        print(f"✗ Retry failed: {e}")

            if status["status"] in ["completed", "failed", "cancelled"]:
                break

            await asyncio.sleep(2)


async def example_4_system_monitoring():
    """
    Example 4: Monitor system health and manage executions
    """
    print("\nExample 4: System Monitoring")
    print("============================")

    async with OrchestrationAPIClient() as client:
        # Get system health
        health = await client.get_health_status()
        print("System Health:")
        print(f"  Total executions: {health['total_executions']}")
        print(f"  Active executions: {health['active_executions']}")
        print(f"  Completed executions: {health['completed_executions']}")
        print(f"  Failed executions: {health['failed_executions']}")

        # List recent executions
        executions = await client.list_executions(limit=5)
        print(f"\nRecent Executions ({executions['total']} total):")
        for execution in executions['executions']:
            print(f"  {execution['execution_id']}: {execution['status']}")

        # Cleanup old executions
        cleanup_result = await client.cleanup_old_executions(max_age_hours=1)
        print(f"\nCleaned up {cleanup_result['cleaned_executions']} old executions")


async def example_5_workflow_cancellation():
    """
    Example 5: Demonstrate workflow cancellation
    """
    print("\nExample 5: Workflow Cancellation")
    print("================================")

    async with OrchestrationAPIClient() as client:
        workflow_def = create_parallel_workflow()

        # Start execution
        await client.create_workflow(workflow_def)
        execution = await client.execute_workflow(
            workflow_def["workflow_id"],
            workflow_def
        )
        execution_id = execution["execution_id"]

        print(f"Started execution: {execution_id}")

        # Let it run for a few seconds
        await asyncio.sleep(3)

        # Cancel the execution
        print("Cancelling execution...")
        await client.cancel_execution(execution_id)

        # Verify cancellation
        status = await client.get_execution_status(execution_id)
        print(f"Execution status after cancellation: {status['status']}")


# Main function to run all examples
async def run_all_examples():
    """
    Run all orchestration API examples
    """
    print("Orchestration API Usage Examples")
    print("================================")
    print("Note: These examples assume the Agent OS server is running at http://localhost:8000")
    print()

    try:
        await example_1_simple_workflow_execution()
        await example_2_parallel_workflow_with_monitoring()
        await example_3_error_handling_and_retry()
        await example_4_system_monitoring()
        await example_5_workflow_cancellation()

        print("\n✓ All examples completed successfully!")

    except Exception as e:
        print(f"\n✗ Example failed with error: {e}")
        print("Make sure the Agent OS server is running and accessible.")


if __name__ == "__main__":
    # Run examples
    asyncio.run(run_all_examples())


# Additional utility functions for testing and development

def create_test_workflow(num_tasks: int = 3, include_dependencies: bool = True) -> Dict[str, Any]:
    """
    Create a test workflow with specified number of tasks
    """
    tasks = []
    for i in range(num_tasks):
        task = {
            "task_id": f"test_task_{i+1}",
            "task_type": "test_processing",
            "agent_id": f"test-agent-{i+1}",
            "depends_on": [f"test_task_{i}"] if include_dependencies and i > 0 else [],
            "data": {
                "iteration": i + 1,
                "test_data": f"data_for_task_{i+1}"
            },
            "timeout_seconds": 120,
            "max_retries": 2
        }
        tasks.append(task)

    return {
        "workflow_id": f"test-workflow-{num_tasks}-tasks",
        "name": f"Test Workflow with {num_tasks} Tasks",
        "description": f"Generated test workflow with {num_tasks} tasks",
        "tasks": tasks,
        "global_timeout_seconds": 600,
        "metadata": {
            "generated": True,
            "num_tasks": num_tasks,
            "test_workflow": True
        }
    }


def print_workflow_summary(workflow_def: Dict[str, Any]):
    """
    Print a summary of a workflow definition
    """
    print(f"Workflow: {workflow_def['name']}")
    print(f"ID: {workflow_def['workflow_id']}")
    print(f"Description: {workflow_def['description']}")
    print(f"Tasks: {len(workflow_def['tasks'])}")
    print("Task Dependencies:")

    for task in workflow_def["tasks"]:
        deps = ", ".join(task["depends_on"]) if task["depends_on"] else "None"
        print(f"  {task['task_id']} -> depends on: {deps}")

    print(f"Global timeout: {workflow_def['global_timeout_seconds']}s")
    print("---")


# Example workflow definitions for different scenarios
EXAMPLE_WORKFLOWS = {
    "simple_sequential": create_simple_sequential_workflow(),
    "parallel_processing": create_parallel_workflow(),
    "conditional_processing": create_conditional_workflow(),
    "test_3_tasks": create_test_workflow(3),
    "test_5_tasks": create_test_workflow(5),
    "test_parallel": create_test_workflow(4, include_dependencies=False),
}
