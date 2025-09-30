# Agent Evaluations

Simple evaluation system following Agno's approach using the API.

## Quick Start

```bash
# Run accuracy evaluations
make eval-accuracy

# Run for specific agent
make eval-accuracy-agent AGENT_ID=your-uuid
```

## How It Works

1. Create JSON config with test cases
2. Script sends evaluation request to `/eval-runs` API endpoint
3. API loads agent from database and runs evaluation using Agno's `AccuracyEval`
4. Results are saved to database and visible in AgnoOS
5. Script displays results with eval ID and link to AgnoOS dashboard

## Example Config

`evals/accuracy/configs/eval_tests.json`:

```json
{
  "agent_id": "your-agent-uuid",
  "test_cases": [
    {
      "name": "Simple addition",
      "input": "What is 2+2?",
      "expected_output": "4",
      "num_iterations": 1
    },
    {
      "name": "Complex with guidelines",
      "input": "What is 10*5 then to the power of 2?",
      "expected_output": "2500",
      "additional_guidelines": "Agent output should include the steps and the final answer.",
      "num_iterations": 1
    }
  ]
}
```

## Test Case Fields

- `name` (string): Test name
- `input` (string): Input to send to agent
- `expected_output` (string): Expected response
- `num_iterations` (number, optional): Number of times to run (default: 1)
- `additional_guidelines` (string, optional): Extra instructions for the evaluator

## Adding Tests

1. Create JSON file in `evals/accuracy/configs/`
2. Run with `--config path/to/config.json`

Pass threshold: 8.0/10.0
