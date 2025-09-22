# AgentOS Integration

Este projeto integra o **AgentOS** da Agno.com com nossa API FastAPI personalizada, permitindo que agentes armazenados no banco de dados sejam automaticamente carregados e disponibilizados através do AgentOS.

## Características Principais

- **Carregamento Dinâmico**: Agentes são carregados automaticamente do banco de dados
- **Configuração Flexível**: Modelos AI diferentes baseados na especialização do agente
- **Integração Transparente**: AgentOS endpoints são adicionados à nossa API existente
- **Gerenciamento em Tempo Real**: Refresh de agentes sem reiniciar a aplicação

## Configuração

### 1. Instalação das Dependências

```bash
pip install agno
```

### 2. Variáveis de Ambiente

Configure as seguintes variáveis no seu `.env`:

```env
# AgentOS Configuration
AGENT_OS_ENABLED=true
AGENT_OS_DEBUG=false
AGENT_OS_DEFAULT_MODEL=gpt-4o-mini

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Agent Loading Configuration
MAX_AGENTS_LOAD=100
LOAD_INACTIVE_AGENTS=false
```

### 3. Modelos por Especialização

O sistema automaticamente seleciona modelos baseado na especialização do agente:

- **data_analyst**: gpt-4o
- **customer_support**: gpt-4o-mini
- **code_reviewer**: gpt-4o
- **content_creator**: gpt-4o
- **research**: gpt-4o
- **general**: gpt-4o-mini (padrão)

## Endpoints da API

### Status do AgentOS
```
GET /api/v1/system/agent-os-status
```

Retorna informações sobre o status da integração:
```json
{
  "agent_os_available": true,
  "agent_os_initialized": true,
  "database_agents_count": 5,
  "active_agents": [...]
}
```

### Refresh de Agentes
```
POST /api/v1/system/refresh-agents
```

Recarrega agentes do banco de dados:
```json
{
  "success": true,
  "message": "Agents refreshed successfully",
  "active_agents": 5
}
```

### Endpoints do AgentOS

Quando o AgentOS está ativo, os seguintes endpoints são automaticamente adicionados:

- `POST /v1/chat/completions` - Chat API compatível com OpenAI
- `GET /v1/agents` - Lista de agentes disponíveis
- `POST /v1/agents/{agent_id}/chat` - Chat direto com um agente específico

## Estrutura do Código

### StartupManager (`app/startup.py`)

- `load_agents_from_database()`: Carrega agentes ativos do banco
- `create_agno_agents()`: Converte agentes do banco para AgentOS
- `initialize_agent_os()`: Inicializa o AgentOS com nossa FastAPI app
- `refresh_agents()`: Atualiza agentes em runtime

### Configuração (`app/config/agent_os_config.py`)

- `AgentOSConfig`: Classe central de configuração
- `get_model_config()`: Seleção de modelo baseada na especialização
- `should_load_agent()`: Filtros para carregamento de agentes

## Fluxo de Inicialização

1. **Startup**: A aplicação inicia e carrega dependências
2. **Database Load**: Agentes ativos são carregados do banco
3. **Agent Creation**: Agentes são convertidos para formato AgentOS
4. **AgentOS Init**: AgentOS é inicializado com a lista de agentes
5. **App Merge**: AgentOS endpoints são mesclados com nossa API

## Exemplo de Uso

### Criando um Agente no Banco

```python
agent = Agent(
    name="Customer Support Bot",
    description="Specialized in customer support",
    specialization="customer_support",
    is_active=True,
    instructions=["Be helpful and polite", "Escalate complex issues"],
    available_tools=["web_search", "knowledge_base"]
)
```

### Usando o AgentOS

```bash
# Via API compatível com OpenAI
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "agent_id_here",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

## Troubleshooting

### AgentOS não inicializa
- Verifique se `agno` está instalado: `pip list | grep agno`
- Confirme OPENAI_API_KEY está configurada
- Verifique logs: erro de modelo ou configuração

### Nenhum agente carregado
- Confirme que existem agentes ativos no banco: `is_active=True`
- Verifique `LOAD_INACTIVE_AGENTS=false` se necessário
- Cheque logs de carregamento no startup

### Endpoints AgentOS não disponíveis
- Confirme `AGENT_OS_ENABLED=true`
- Verifique se houve erro na inicialização
- Use `/api/v1/system/agent-os-status` para diagnóstico