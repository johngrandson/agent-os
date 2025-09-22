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

            self.knowledge_service = self.container.knowledge_service()
            print("✅ Serviço de conhecimento carregado")
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

    async def seed_knowledge(self, agents: List[Agent]):
        """Criar conhecimento básico para os agentes"""
        print(f"🔍 Iniciando criação de conhecimento para {len(agents)} agentes...")
        for agent in agents:
            print(f"   📋 Agente disponível: {agent.name} (ID: {agent.id})")

        knowledge_data = [
            {
                "name": "Políticas da Empresa",
                "description": "Políticas gerais e código de conduta da empresa",
                "content_type": "policy",
                "content": """
                POLÍTICAS GERAIS DA EMPRESA

                1. HORÁRIO DE FUNCIONAMENTO
                - Segunda a Sexta: 8h às 18h
                - Sábado: 8h às 12h
                - Domingo e feriados: Fechado

                2. POLÍTICA DE ATENDIMENTO
                - Tempo máximo de resposta: 24 horas
                - Atendimento prioritário para clientes premium
                - Sempre manter cortesia e profissionalismo

                3. POLÍTICA DE DEVOLUÇÃO
                - Prazo: 30 dias após a compra
                - Produto deve estar em perfeitas condições
                - Nota fiscal obrigatória

                4. CANAIS DE ATENDIMENTO
                - WhatsApp: +55 11 99999-9999
                - Email: contato@empresa.com.br
                - Site: www.empresa.com.br
                """,
            },
            {
                "name": "Produtos e Serviços",
                "description": "Catálogo completo de produtos e serviços oferecidos",
                "content_type": "catalog",
                "content": """
                CATÁLOGO DE PRODUTOS E SERVIÇOS

                1. CATEGORIA TECNOLOGIA
                - Desenvolvimento de Software: R$ 5.000 - R$ 50.000
                - Consultoria em TI: R$ 200/hora
                - Suporte Técnico: R$ 100/hora
                - Hospedagem de Sites: R$ 29,90/mês

                2. CATEGORIA MARKETING
                - Gestão de Redes Sociais: R$ 1.500/mês
                - Criação de Sites: R$ 2.500 - R$ 15.000
                - Campanhas Google Ads: R$ 800/mês + investimento
                - Design Gráfico: R$ 150 - R$ 500 por peça

                3. CATEGORIA CONSULTORIA
                - Consultoria Empresarial: R$ 300/hora
                - Planejamento Estratégico: R$ 8.000 - R$ 25.000
                - Análise de Processos: R$ 5.000 - R$ 15.000

                4. PROMOÇÕES ATIVAS
                - 20% desconto para novos clientes
                - Pacote básico grátis no primeiro mês
                - Desconto progressivo para contratos anuais
                """,
            },
            {
                "name": "Perguntas Frequentes",
                "description": "Respostas para as dúvidas mais comuns dos clientes",
                "content_type": "faq",
                "content": """
                PERGUNTAS FREQUENTES (FAQ)

                1. COMO FAZER UM PEDIDO?
                Entre em contato pelo WhatsApp, email ou site. Nossa equipe fará um orçamento personalizado.

                2. QUAIS AS FORMAS DE PAGAMENTO?
                Aceitamos: PIX, cartão de crédito (até 12x), boleto bancário e transferência.

                3. QUAL O PRAZO DE ENTREGA?
                Varia conforme o projeto:
                - Sites simples: 7-15 dias
                - Sistemas complexos: 30-90 dias
                - Design gráfico: 2-5 dias

                4. OFERECEM SUPORTE PÓS-VENDA?
                Sim! 3 meses de suporte gratuito incluído. Após esse período, oferecemos planos de manutenção.

                5. TRABALHAM COM EMPRESAS DE OUTROS ESTADOS?
                Sim, atendemos todo o Brasil remotamente.

                6. COMO SOLICITAR ALTERAÇÕES?
                Até 3 revisões incluídas no projeto. Alterações extras são cobradas à parte.

                7. FAZEM CONTRATOS DE LONGO PRAZO?
                Sim, oferecemos descontos especiais para contratos anuais.
                """,
            },
            {
                "name": "Benefícios dos Funcionários",
                "description": "Informações sobre benefícios e políticas de RH",
                "content_type": "hr",
                "content": """
                BENEFÍCIOS DOS FUNCIONÁRIOS

                1. BENEFÍCIOS OBRIGATÓRIOS
                - Vale Transporte (100% custeado)
                - Vale Alimentação: R$ 25/dia
                - Plano de Saúde (funcionário + dependentes)
                - Seguro de Vida em Grupo

                2. BENEFÍCIOS ADICIONAIS
                - Gympass ou similar: R$ 30/mês
                - Day off no aniversário
                - Horário flexível (7h-9h entrada)
                - Home office 2x na semana
                - Participação nos Lucros (PLR)

                3. POLÍTICAS DE FÉRIAS
                - 30 dias corridos após 12 meses
                - Possibilidade de vender 10 dias
                - Férias podem ser divididas em até 3 períodos

                4. LICENÇAS E AFASTAMENTOS
                - Licença maternidade: 180 dias
                - Licença paternidade: 20 dias
                - Acompanhamento médico: até 4h/mês

                5. DESENVOLVIMENTO PROFISSIONAL
                - Orçamento anual para cursos: R$ 2.000
                - Participação em eventos (custeado)
                - Programa de mentoria interna
                """,
            },
            {
                "name": "Destinos de Viagem",
                "description": "Informações sobre destinos turísticos populares",
                "content_type": "travel",
                "content": """
                DESTINOS DE VIAGEM - BRASIL

                1. NORDESTE
                - Salvador (BA): Pelourinho, praias, cultura afro-brasileira
                - Recife/Olinda (PE): Marco Zero, frevo, beaches
                - Fortaleza (CE): Praia do Futuro, dunas, jangadas
                - Natal (RN): Ponta Negra, Genipabu, cajueiro
                - Maceió (AL): Praia do Francês, piscinas naturais

                2. SUDESTE
                - Rio de Janeiro: Cristo Redentor, Copacabana, Pão de Açúcar
                - São Paulo: Museus, gastronomia, vida noturna
                - Campos do Jordão: Clima europeu, fondue, chocolate
                - Ouro Preto (MG): História, arquitetura colonial

                3. SUL
                - Gramado/Canela (RS): Natal Luz, chocolates, natureza
                - Florianópolis (SC): Praia da Joaquina, Lagoa da Conceição
                - Curitiba (PR): Parques, Jardim Botânico

                4. CENTRO-OESTE
                - Pantanal: Safari, pesca, natureza
                - Chapada dos Guimarães: Cachoeiras, trilhas
                - Bonito (MS): Águas cristalinas, mergulho

                5. NORTE
                - Manaus (AM): Teatro Amazonas, encontro das águas
                - Alter do Chão (PA): Caribe amazônico
                """,
            },
        ]

        # Associar conhecimento aos agentes apropriados
        agent_knowledge_mapping = {
            "Assistente Virtual": [
                "Políticas da Empresa",
                "Produtos e Serviços",
                "Perguntas Frequentes",
            ]
        }

        for knowledge_item in knowledge_data:
            print(f"🔧 Processando conhecimento: {knowledge_item['name']}")
            # Encontrar agentes que devem ter esse conhecimento
            target_agents = []
            for agent in agents:
                if agent.name in agent_knowledge_mapping:
                    if knowledge_item["name"] in agent_knowledge_mapping[agent.name]:
                        target_agents.append(agent)
                        print(f"Agente {agent.name} deve receber este conhecimento")
                    else:
                        print(f"Agente {agent.name} não precisa deste conhecimento")
                else:
                    print(f"Agente {agent.name} não está no mapeamento")

            print(f"Total de agentes target: {len(target_agents)}")

            # Criar conhecimento para cada agente target
            for agent in target_agents:
                try:
                    # Verificar se conhecimento já existe
                    existing_contents = (
                        await self.knowledge_service.get_agent_knowledge_contents(
                            agent_id=agent.id, limit=100
                        )
                    )
                    existing_names = [content.name for content in existing_contents]

                    if knowledge_item["name"] in existing_names:
                        print(
                            f"Conhecimento '{knowledge_item['name']}' já existe para {agent.name}"
                        )
                        continue

                    knowledge = await self.knowledge_service.add_content(
                        agent_id=agent.id,
                        name=knowledge_item["name"],
                        content=knowledge_item["content"],
                        description=knowledge_item["description"],
                    )
                    print(
                        f"📚 Criado conhecimento '{knowledge.name}' para {agent.name}"
                    )
                except Exception as e:
                    error_type = type(e).__name__
                    error_message = str(e)
                    agent_name = getattr(agent, "name", f"Agent ID {agent.id}")
                    print(
                        f"❌ Erro ao criar conhecimento '{knowledge_item['name']}' para {agent_name}: {error_type}"
                    )
                    print(f"   📋 Detalhes: {error_message}")
                    import traceback

                    print(f"   📊 Stack trace:")
                    traceback.print_exc()

    async def run(self):
        """Executar o seeder completo"""
        print("🚀 Iniciando seeder de agentes e conhecimento...")

        try:
            # Configurar contexto de sessão
            from infrastructure.database.session import set_session_context

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

                await self.seed_knowledge(agents)
                print("✅ Conhecimento criado para os agentes")

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
