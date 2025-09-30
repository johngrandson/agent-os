#!/usr/bin/env python
"""
Accuracy evaluation script using our custom API endpoint.
Uses configured agents with KnowledgeTools and custom instructions.
Results are automatically saved to AgentOS database.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# API Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
ACCURACY_EVAL_ENDPOINT = f"{API_BASE_URL}/api/v1/accuracy-eval"
EVAL_FEEDBACK_ENDPOINT = f"{API_BASE_URL}/api/v1/eval-feedback"


def load_test_config(config_path: str) -> dict:
    """Load test configuration from JSON file"""
    with open(config_path) as f:
        return json.load(f)


def run_eval_via_custom_api(
    agent_id: str,
    eval_name: str,
    test_case: dict,
) -> dict | None:
    """
    Run accuracy evaluation via our custom API endpoint.

    Uses configured agent with:
    - KnowledgeTools (think, search, analyze)
    - Custom instructions
    - Same configuration as webhook/AgentOS agents

    Args:
        agent_id: Agent UUID
        eval_name: Name for this evaluation
        test_case: Test case configuration

    Returns:
        API response with eval results
    """
    payload = {
        "name": eval_name,
        "agent_id": agent_id,
        "input": test_case["input"],
        "expected_output": test_case["expected_output"],
        "num_iterations": test_case.get("num_iterations", 1),
    }

    # Add optional fields
    if "additional_guidelines" in test_case:
        payload["additional_guidelines"] = test_case["additional_guidelines"]

    try:
        response = requests.post(
            ACCURACY_EVAL_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=120,  # 2 minutes timeout for eval
        )
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"  ✗ API Error: {e}")
        return None


def process_eval_feedback(eval_id: str, agent_id: str) -> bool:
    """
    Process evaluation feedback if score < 8.0

    Args:
        eval_id: Evaluation ID
        agent_id: Agent ID

    Returns:
        True if feedback was processed successfully
    """
    try:
        response = requests.post(
            EVAL_FEEDBACK_ENDPOINT,
            json={"eval_id": eval_id, "agent_id": agent_id},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )

        if response.status_code == 201:
            return True
        elif response.status_code == 400:
            # Evaluation passed, no feedback needed
            return False
        else:
            print(f"  ⚠ Feedback processing returned {response.status_code}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"  ⚠ Failed to process feedback: {e}")
        return False


def run_evaluations(config_path: str) -> bool:
    """
    Run accuracy evaluations from config file using custom API.

    Args:
        config_path: Path to JSON config file

    Returns:
        True if all tests passed, False otherwise
    """
    print(f"\n{'=' * 70}")
    print("Running Accuracy Evaluations (Custom API - Configured Agents)")
    print(f"{'=' * 70}\n")

    # Load test configuration
    test_config = load_test_config(config_path)
    agent_id = test_config["agent_id"]
    test_cases = test_config["test_cases"]

    # Get auto-process setting
    auto_process = os.getenv("AUTO_PROCESS_EVAL_FAILURES", "false").lower() == "true"

    print(f"Agent ID: {agent_id}")
    print(f"Config: {config_path}")
    print(f"API Endpoint: {ACCURACY_EVAL_ENDPOINT}")
    print(f"Auto-process failures: {auto_process}")

    # Filter active test cases
    active_tests = [tc for tc in test_cases if tc.get("active", True)]
    print(f"\nRunning {len(active_tests)} active test case(s)...\n")

    results = []
    total_score = 0.0

    for idx, test_case in enumerate(test_cases, 1):
        if not test_case.get("active", True):
            print(f"Skipping inactive test: {test_case['name']}")
            continue

        print(f"{'-' * 70}\n")
        print(f"Test {idx}/{len(test_cases)}: {test_case['name']}")
        print(f"  Input: {test_case['input']}")
        print(f"  Expected: {test_case['expected_output'][:60]}...")
        print(f"  Iterations: {test_case.get('num_iterations', 1)}")

        if "additional_guidelines" in test_case:
            print(f"  Guidelines: {test_case['additional_guidelines'][:60]}...")

        print("  Running via Custom API...")

        # Run evaluation
        result = run_eval_via_custom_api(agent_id, test_case["name"], test_case)

        if result:
            score = result.get("avg_score", 0)
            status = result.get("status", "unknown")
            eval_id = result.get("eval_id", "unknown")

            # Color output based on pass/fail
            if status == "passed":
                print(f"  \033[92m✓ PASS\033[0m - Score: {score}/10.0")
            else:
                print(f"  \033[91m✗ FAIL\033[0m - Score: {score}/10.0")

            print(f"  Eval ID: {eval_id}")

            results.append({"name": test_case["name"], "score": score, "status": status})
            total_score += score

            # Auto-process feedback if enabled and eval failed
            if auto_process and status == "failed" and eval_id != "unknown":
                if process_eval_feedback(eval_id, agent_id):
                    print("  📚 Auto-added feedback to agent knowledge")

        else:
            print("  ✗ FAIL - API call failed")
            results.append({"name": test_case["name"], "score": 0, "status": "failed"})

    # Print summary
    print(f"\n{'-' * 70}\n")
    print("Summary:")
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = len(results) - passed
    avg_score = total_score / len(results) if results else 0

    print(f"  Total Tests: {len(test_cases)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Average Score: {avg_score:.1f}/10.0")

    print(f"\n{'=' * 70}")
    if failed == 0:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")
    print(f"{'=' * 70}\n")

    return failed == 0


def main() -> int:
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run accuracy evaluations using configured agents")
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Path to JSON config file with test cases",
    )

    args = parser.parse_args()

    if not Path(args.config).exists():
        print(f"Error: Config file not found: {args.config}")
        return 1

    try:
        success = run_evaluations(args.config)
        return 0 if success else 1
    except Exception as e:
        print(f"Error running evaluations: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
