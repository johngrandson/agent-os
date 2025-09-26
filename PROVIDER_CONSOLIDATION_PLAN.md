# Provider Module Consolidation Plan

## Problem Analysis

### Current State
- `app/integrations/agno/` - Contains core agno functionality
- `app/providers/` - Contains abstractions that wrap integrations
- **Issue**: AgnoProvider imports from integrations, creating unclear responsibility

### Dependencies Found
**Files importing from app.integrations:**
- `/home/joao/decod3/agent-os/app/providers/agno_provider.py`
- `/home/joao/decod3/agent-os/app/integrations/agno/agent_converter.py`

**Key imports to fix:**
```python
from app.integrations.agno.agent_converter import AgnoAgentConverter
from app.integrations.agno.knowledge_adapter import AgnoKnowledgeAdapter
from app.integrations.agno.model_factory import AgnoModelFactory
```

## Proposed Solution

### Single Module Structure
```
app/providers/
├── __init__.py                 # Main provider exports
├── base.py                     # RuntimeAgent + AgentProvider interfaces
├── factory.py                  # Provider selection logic
└── agno/                       # All agno implementation
    ├── __init__.py             # Agno-specific exports
    ├── provider.py             # AgnoProvider (renamed from agno_provider.py)
    ├── agent_converter.py      # Moved from integrations/agno/
    ├── knowledge_adapter.py    # Moved from integrations/agno/
    ├── model_factory.py        # Moved from integrations/agno/
    └── config.py              # Moved from integrations/agno/
```

### Benefits
1. **Clear ownership**: All provider code in one place
2. **No circular dependencies**: agno code lives under providers
3. **Simple imports**: Single module for all provider functionality
4. **Future-ready**: Easy to add providers/crewai/ later
5. **Follows CLAUDE.md**: Boring, obvious structure

## Migration Stages

### Stage 1: Create New Structure
- Create `app/providers/agno/` directory
- Move agno_provider.py to providers/agno/provider.py
- Update imports within the moved file

### Stage 2: Move Integration Files
- Move all files from `app/integrations/agno/` to `app/providers/agno/`
- Update internal imports (self-referencing within agno module)
- Keep external API the same initially

### Stage 3: Update All Imports
- Update factory.py to import from new location
- Update any other files importing agno provider
- Run tests to verify everything works

### Stage 4: Cleanup
- Remove empty `app/integrations/` directory
- Update provider __init__.py exports
- Final test run

## Risk Mitigation
- Each stage maintains working tests
- No changes to external interfaces initially
- Incremental commits after each working stage
- Rollback plan: git revert if issues arise

## Success Criteria
- All tests pass (currently 98.9%)
- Single clear provider module structure
- No circular dependencies
- Clean, obvious import paths
