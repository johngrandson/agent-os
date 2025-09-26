# Agent Integration Tests

This directory contains comprehensive integration tests for the Agent CRUD operations in the `app/agents/` directory.

## Test Structure

### Test Files Overview

- **`conftest.py`** - Test fixtures, database setup, and testing utilities
- **`test_agent_repository.py`** - Repository layer integration tests
- **`test_agent_service.py`** - Service layer business logic tests
- **`test_agent_api.py`** - API endpoint integration tests
- **`test_agent_edge_cases.py`** - Edge cases, error scenarios, and constraints
- **`test_agent_events.py`** - Event publishing integration tests

## Test Categories

### Repository Layer Tests (`test_agent_repository.py`)
- **Create Operations**: Agent persistence, ID generation, field validation
- **Read Operations**: Retrieval by ID, phone number, pagination, filtering
- **Update Operations**: Field updates, timestamp handling, persistence verification
- **Delete Operations**: Removal verification, cascade behavior
- **Constraints**: Unique phone numbers, field length limits
- **Edge Cases**: Unicode handling, large data sets, concurrent operations

### Service Layer Tests (`test_agent_service.py`)
- **Business Logic**: Validation rules, duplicate prevention
- **Transaction Management**: Atomic operations with event publishing
- **Error Handling**: Service-level exception management
- **Event Integration**: Verification of event publishing triggers
- **UUID Conversion**: String to UUID handling and validation
- **Command Processing**: Request command transformation and validation

### API Layer Tests (`test_agent_api.py`)
- **HTTP Endpoints**: All CRUD endpoints (GET, POST, PUT, DELETE)
- **Request Validation**: Pydantic model validation, field requirements
- **Response Format**: Correct serialization, status codes, error responses
- **Pagination**: Limit enforcement, parameter validation
- **Error Responses**: 400, 404, 409, 422 status codes
- **Data Serialization**: UUID to string conversion, null field handling

### Edge Cases and Error Scenarios (`test_agent_edge_cases.py`)
- **Database Constraints**: Field length limits, unique constraints
- **Special Characters**: Unicode, emojis, JSON characters, international text
- **Concurrency**: Race conditions, concurrent operations
- **Data Boundaries**: Maximum field lengths, large datasets
- **Error Recovery**: Database errors, connection failures
- **Invalid Input**: Malformed UUIDs, invalid data types

### Event Integration Tests (`test_agent_events.py`)
- **Event Publishing**: Creation, update, and deletion events
- **Event Data**: Correct payload structure and content
- **Event Failures**: Error handling when event publishing fails
- **Transaction Rollback**: Ensuring atomicity with event publishing
- **Event Consistency**: Agent ID consistency across event types
- **Publisher Integration**: Dependency injection and interface verification

## Test Infrastructure

### Database Testing
- **In-Memory SQLite**: Fast, isolated test database
- **Transaction Management**: Each test runs in isolated transaction
- **Schema Creation**: Automatic table creation/cleanup
- **Session Management**: Proper async session handling

### Fixtures and Factories
- **AgentFactory**: Test data generation with sensible defaults
- **Database Fixtures**: Pre-configured test database and sessions
- **Mock Services**: Event publishers and external dependencies
- **Sample Data**: Realistic test data for various scenarios

### Test Utilities
- **Custom Markers**: Categorize tests by layer and functionality
- **Async Support**: Full async/await test support
- **Error Simulation**: Mock failures for resilience testing
- **Parameterized Tests**: Multiple scenarios with single test functions

## Running the Tests

### Run All Agent Integration Tests
```bash
pytest tests/integration/agents/ -v
```

### Run Specific Test Categories
```bash
# Repository tests only
pytest tests/integration/agents/test_agent_repository.py -v

# Service tests only
pytest tests/integration/agents/test_agent_service.py -v

# API tests only
pytest tests/integration/agents/test_agent_api.py -v

# Edge cases only
pytest tests/integration/agents/test_agent_edge_cases.py -v

# Event tests only
pytest tests/integration/agents/test_agent_events.py -v
```

### Run Tests by Markers
```bash
# Database-related tests
pytest tests/integration/agents/ -m database -v

# Event-related tests
pytest tests/integration/agents/ -m events -v

# Repository layer tests
pytest tests/integration/agents/ -m agent_repository -v

# Service layer tests
pytest tests/integration/agents/ -m agent_service -v

# API tests
pytest tests/integration/agents/ -m agent_api -v
```

### Run with Coverage
```bash
pytest tests/integration/agents/ --cov=app.agents --cov-report=html
```

## Test Design Principles

### TDD Approach
- **Red-Green-Refactor**: Tests written before implementation
- **Behavior-Driven**: Tests focus on expected behavior, not implementation
- **Clear Naming**: Descriptive test names indicating scenario and expectation

### Test Independence
- **Isolated Tests**: Each test can run independently
- **Clean State**: Database reset between tests
- **No Side Effects**: Tests don't affect each other

### Comprehensive Coverage
- **Happy Path**: Normal operation scenarios
- **Edge Cases**: Boundary conditions and unusual inputs
- **Error Cases**: Exception handling and failure scenarios
- **Integration Points**: Cross-layer interaction verification

### Realistic Testing
- **Production-Like Data**: Realistic test data reflecting actual usage
- **Real Constraints**: Database constraints and business rules
- **Error Simulation**: Realistic failure scenarios
- **Performance Considerations**: Large datasets and concurrent operations

## Test Data Management

### Agent Factory Patterns
```python
# Basic agent creation
agent = agent_factory.build_agent()

# Agent with specific data
agent = agent_factory.build_agent(
    name="Custom Agent",
    is_active=True,
    llm_model="gpt-4"
)

# Multiple agents
agents = agent_factory.build_agents(count=5)

# Command objects
command = agent_factory.build_create_command()
update_command = agent_factory.build_update_command(agent_id="...")
```

### Fixture Usage
```python
# Pre-persisted agent
def test_with_existing_agent(persisted_agent: Agent):
    # Agent is already in database

# Multiple agents
def test_with_multiple_agents(persisted_agents: List[Agent]):
    # Multiple agents already in database

# Mock event publisher
def test_event_handling(mock_event_publisher):
    # Event publisher is mocked for testing
```

## Continuous Integration

### Test Requirements
- **Python 3.11+**: Async/await support and type hints
- **pytest-asyncio**: Async test execution
- **SQLAlchemy 2.0+**: Modern async ORM features
- **FastAPI**: API testing framework

### Performance Goals
- **Fast Execution**: In-memory database for speed
- **Parallel Execution**: Tests designed for parallel runs
- **Quick Feedback**: Fail fast on errors

### Quality Gates
- **100% Test Pass Rate**: All tests must pass
- **High Coverage**: Aim for >90% code coverage
- **No Flaky Tests**: Deterministic, reliable execution
- **Clear Failures**: Descriptive error messages

## Contributing

### Adding New Tests
1. Follow existing naming conventions
2. Use appropriate test markers
3. Include both happy path and error scenarios
4. Add edge cases for new functionality
5. Update this README if adding new test categories

### Test Maintenance
1. Keep tests focused and atomic
2. Use factories for test data creation
3. Mock external dependencies appropriately
4. Maintain test independence
5. Update tests when business logic changes
