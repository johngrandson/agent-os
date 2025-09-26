# Provider Abstraction Implementation Plan

## Overview
Decouple the application from agno-specific code to enable future provider switching. Use the simplest approach that works - wrap existing agno functionality behind a thin interface layer.

## Current Coupling Analysis

### Direct agno Dependencies Found
- **Container (`app/container.py`)**: Lines 13, 104-119 - Direct instantiation of Agno-specific services
- **Initialization (`app/initialization.py`)**: Lines 9-10, 29, 50, 57, 83, 91 - Direct AgnoAgent and AgentOS imports
- **Knowledge Factory (`app/knowledge/services/agent_knowledge_factory.py`)**: Lines 31-34 - Direct agno imports
- **Agno Integration Module (`app/integrations/agno/`)**: Entire module is provider-specific

### Simple Solution
Create a thin `app/providers/` layer that:
1. Defines minimal interfaces for what we actually need to switch
2. Wraps existing agno functionality
3. Uses environment variables for provider selection
4. Maintains existing behavior exactly

---

## Stage 1: Simple Provider Interface

**Goal**: Create minimal interface to wrap agno functionality
**Success Criteria**: Can switch from direct agno imports to provider interface, all tests pass
**Tests**: Existing functionality works through new interface
**Status**: Complete

### Simple Structure
```
app/providers/
├── __init__.py               # Simple exports
├── base.py                   # Minimal interfaces
├── agno_provider.py          # Wrap existing agno code
└── factory.py               # Simple provider factory
```

### What We Actually Need
Just these 3 interfaces based on current usage:
1. **Agent conversion** - convert DB agents to runtime agents
2. **Agent execution** - run agents with messages
3. **Runtime setup** - setup FastAPI with agents

### 1.1: Minimal Interfaces

Create `app/providers/base.py` with just what we need:

```python
# app/providers/base.py
from abc import ABC, abstractmethod
from typing import List, Any
from fastapi import FastAPI

class RuntimeAgent(ABC):
    """Simple wrapper for runtime agents"""

    @abstractmethod
    async def run(self, message: str) -> str:
        """Run agent with message, return response"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        pass

class AgentProvider(ABC):
    """Convert DB agents to runtime agents"""

    @abstractmethod
    async def convert_agents_for_webhook(self, db_agents: List[Any]) -> List[RuntimeAgent]:
        pass

    @abstractmethod
    async def convert_agents_for_runtime(self, db_agents: List[Any]) -> List[RuntimeAgent]:
        pass

    @abstractmethod
    def setup_runtime_with_app(self, agents: List[RuntimeAgent], app: FastAPI) -> FastAPI:
        pass
```

### 1.2: Agno Provider Implementation

Create `app/providers/agno_provider.py` - just wrap existing code:

```python
# app/providers/agno_provider.py
from .base import AgentProvider, RuntimeAgent
# Import existing agno stuff and wrap it
```

### 1.3: Simple Factory

Create `app/providers/factory.py`:

```python
# app/providers/factory.py
import os
from .base import AgentProvider
from .agno_provider import AgnoProvider

def get_provider() -> AgentProvider:
    provider_name = os.getenv("AGENT_PROVIDER", "agno")
    if provider_name == "agno":
        return AgnoProvider()
    # Add other providers later
    raise ValueError(f"Unknown provider: {provider_name}")
```

---

## Stage 2: Replace Direct Imports

**Goal**: Replace agno imports with provider factory calls
**Success Criteria**: No direct agno imports in core app, all functionality works
**Tests**: All existing tests pass
**Status**: Complete

### Simple Changes
1. In `app/container.py` - use provider factory instead of agno classes
2. In `app/initialization.py` - use provider instead of direct AgentOS
3. In `app/webhook/` - use provider agents instead of AgnoAgent
4. Replace other direct imports with provider calls

### Example: Container Changes

Instead of:
```python
# Direct agno import
from app.integrations.agno.agent_converter import AgnoAgentConverter
converter = AgnoAgentConverter()
```

Use:
```python
# Provider factory
from app.providers.factory import get_provider
provider = get_provider()
```

---

## Stage 3: Test and Cleanup

**Goal**: Verify everything works and clean up
**Success Criteria**: All tests pass, agno integration still in place as fallback
**Tests**: All existing tests, basic provider switching test
**Status**: Complete

### Validation
1. Run all existing tests
2. Test switching provider via environment variable
3. Verify webhook processing still works
4. Verify agent creation still works

---

## Implementation Notes

### Keep It Simple
- Only 3 files needed: `base.py`, `agno_provider.py`, `factory.py`
- No complex registries, factories, or configuration systems
- Use environment variables for provider selection
- Wrap existing code, don't rewrite it

### Future Providers
When adding CrewAI or others:
1. Create `crew_ai_provider.py` that implements `AgentProvider`
2. Add case to `factory.py`
3. That's it - no complex registration needed

### Migration Path
1. **Stage 1**: Create provider interfaces and agno wrapper
2. **Stage 2**: Replace direct imports with provider factory
3. **Stage 3**: Test and validate
4. **Future**: Add new providers as simple new files

### What NOT to Do
- Don't create complex factory patterns
- Don't create elaborate configuration systems
- Don't create multiple abstract interface files
- Don't create registries or dependency injection for this
- Don't create extensive adapter patterns

### Environment Variables
```bash
# Use agno (default)
AGENT_PROVIDER=agno

# Use crewai (future)
AGENT_PROVIDER=crewai
```

This approach follows CLAUDE.md principles:
- **Boring over clever**: Simple factory function
- **Incremental**: Can add providers one at a time
- **Learning from existing**: Wraps current agno code
- **Single responsibility**: Each file has one clear purpose
- **No premature abstraction**: Only abstract what we need to switch

The entire provider system should be under 200 lines of code total.
