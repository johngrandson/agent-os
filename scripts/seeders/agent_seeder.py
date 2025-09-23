#!/usr/bin/env python3
"""
Seeder para criar agentes básicos e conhecimento em português (pt-BR)
"""

import asyncio
import sys
import os
import uuid
from pathlib import Path
from typing import List

# Adicionar o diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from app.container import ApplicationContainer as Container
from app.agents.agent import Agent
from app.agents.api.schemas import CreateAgentCommand
from infrastructure.database import Base
from infrastructure.database.session import engines, EngineType


class AgentSeeder:
    def __init__(self):
        print("🔧 Inicializando AgentSeeder...")
        try:
            self.container = Container()
            print("✅ Container de dependências criado")

            self.agent_service = self.container.agent_service()
            print("✅ Serviço de agentes carregado")

        except Exception as e:
            print(f"❌ Erro na inicialização: {type(e).__name__}")
            print(f"   📋 Detalhes: {str(e)}")
            import traceback

            traceback.print_exc()
            raise

    async def create_tables(self):
        """Criar tabelas se não existirem"""
        async with engines[EngineType.WRITER].begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def seed_agents(self) -> List[Agent]:
        """Criar agentes básicos em português"""
        agents_data = [
            {
                "name": "Assistente Virtual",
                "phone_number": "+5511999999001",
                "description": "Assistente virtual inteligente para atendimento ao cliente e suporte geral",
                "instructions": [
                    "Seja sempre educado e prestativo",
                    "Responda em português do Brasil",
                    "Mantenha as respostas claras e objetivas",
                    "Se não souber a resposta, seja honesto e informe que não sabe",
                ],
                "is_active": True,
            }
        ]

        created_agents = []
        for agent_data in agents_data:
            try:
                # Criar comando para o serviço
                command = CreateAgentCommand(**agent_data)

                # Tentar criar o agente - se já existir, vai dar erro
                agent = await self.agent_service.create_agent(command=command)
                created_agents.append(agent)
                status = "✅ ATIVO" if agent.is_active else "⏸️  INATIVO"
                print(f"✨ Criado: {agent.name} ({agent.phone_number}) - {status}")
            except Exception as e:
                # Log detalhado do erro
                error_type = type(e).__name__
                error_message = str(e)

                # Se der erro de agente já existe, não é erro crítico
                if (
                    "AgentAlreadyExists" in error_type
                    or "already exists" in error_message.lower()
                ):
                    print(
                        f"⚠️  Agente {agent_data['name']} já existe (telefone: {agent_data['phone_number']})"
                    )
                    print(f"   📋 Detalhes: {error_type} - {error_message}")
                else:
                    print(f"❌ Erro ao criar agente {agent_data['name']}: {error_type}")
                    print(f"   📋 Detalhes: {error_message}")
                    print(f"   🔍 Tipo do erro: {error_type}")
                    # Log do traceback para debugging
                    import traceback

                    print(f"   📊 Stack trace:")
                    traceback.print_exc()

        return created_agents

    async def run(self):
        """Executar o seeder"""
        from infrastructure.database.session import set_session_context

        try:
            session_id = str(uuid.uuid4())
            print(f"🔧 Configurando sessão com ID: {session_id}")
            context_token = set_session_context(session_id)
            print("✅ Contexto de sessão configurado")

            try:
                await self.create_tables()
                print("✅ Tabelas verificadas/criadas")

                agents = await self.seed_agents()
                print(f"✅ {len(agents)} agentes criados")

                # Se nenhum agente foi criado (já existem), buscar da base de dados
                if not agents:
                    print("🔍 Buscando agentes existentes da base de dados...")
                    existing_agents = await self.agent_service.get_agent_list(limit=100)
                    agents = existing_agents
                    print(f"✅ {len(agents)} agentes encontrados na base de dados")

                print("🎉 Seeder executado com sucesso!")

            finally:
                # Limpar contexto
                from infrastructure.database.session import reset_session_context

                reset_session_context(context_token)

        except Exception as e:
            error_type = type(e).__name__
            error_message = str(e)
            print(f"❌ Erro durante execução do seeder: {error_type}")
            print(f"   📋 Detalhes: {error_message}")
            import traceback

            print(f"   📊 Stack trace completo:")
            traceback.print_exc()
            raise


async def main():
    """Função principal"""
    seeder = AgentSeeder()
    await seeder.run()


if __name__ == "__main__":
    asyncio.run(main())
