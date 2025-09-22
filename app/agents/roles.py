"""
Agent roles and specializations
"""

from enum import Enum


class AgentRole(str, Enum):
    """Predefined agent roles"""

    ASSISTANT = "assistant"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    COORDINATOR = "coordinator"
    EXECUTOR = "executor"
    CUSTOMER_SERVICE = "customer_service"
    SALES = "sales"
    SUPPORT = "support"
    MODERATOR = "moderator"


class AgentSpecialization(str, Enum):
    """Predefined agent specializations"""

    # General
    GENERAL_PURPOSE = "general_purpose"

    # Customer Service
    CUSTOMER_SUPPORT = "customer_support"
    TECHNICAL_SUPPORT = "technical_support"
    BILLING_SUPPORT = "billing_support"

    # Sales & Marketing
    SALES_REPRESENTATIVE = "sales_representative"
    LEAD_QUALIFICATION = "lead_qualification"
    PRODUCT_SPECIALIST = "product_specialist"

    # Content & Research
    CONTENT_CREATOR = "content_creator"
    MARKET_RESEARCHER = "market_researcher"
    DATA_ANALYST = "data_analyst"

    # Specialized Tasks
    APPOINTMENT_SCHEDULER = "appointment_scheduler"
    ORDER_PROCESSOR = "order_processor"
    FAQ_RESPONDER = "faq_responder"


def get_role_tools(role: AgentRole) -> list[str]:
    """Get default tools for a specific role"""

    role_tools = {
        AgentRole.ASSISTANT: ["text_analyzer"],
        AgentRole.RESEARCHER: ["web_search", "text_analyzer", "text_summarizer"],
        AgentRole.ANALYST: ["text_analyzer", "text_summarizer"],
        AgentRole.COORDINATOR: ["text_analyzer"],
        AgentRole.EXECUTOR: ["text_analyzer"],
        AgentRole.CUSTOMER_SERVICE: ["text_analyzer", "text_summarizer"],
        AgentRole.SALES: ["text_analyzer", "web_search"],
        AgentRole.SUPPORT: ["text_analyzer", "text_summarizer", "web_search"],
        AgentRole.MODERATOR: ["text_analyzer"],
    }

    return role_tools.get(role, [])


def get_specialization_tools(specialization: AgentSpecialization) -> list[str]:
    """Get default tools for a specific specialization"""

    specialization_tools = {
        AgentSpecialization.GENERAL_PURPOSE: ["text_analyzer"],
        AgentSpecialization.CUSTOMER_SUPPORT: ["text_analyzer", "text_summarizer"],
        AgentSpecialization.TECHNICAL_SUPPORT: ["text_analyzer", "web_search"],
        AgentSpecialization.BILLING_SUPPORT: ["text_analyzer"],
        AgentSpecialization.SALES_REPRESENTATIVE: ["text_analyzer", "web_search"],
        AgentSpecialization.LEAD_QUALIFICATION: ["text_analyzer"],
        AgentSpecialization.PRODUCT_SPECIALIST: ["text_analyzer", "web_search"],
        AgentSpecialization.CONTENT_CREATOR: [
            "text_analyzer",
            "text_summarizer",
            "web_search",
        ],
        AgentSpecialization.MARKET_RESEARCHER: [
            "web_search",
            "text_analyzer",
            "text_summarizer",
        ],
        AgentSpecialization.DATA_ANALYST: ["text_analyzer", "text_summarizer"],
        AgentSpecialization.APPOINTMENT_SCHEDULER: ["text_analyzer"],
        AgentSpecialization.ORDER_PROCESSOR: ["text_analyzer"],
        AgentSpecialization.FAQ_RESPONDER: ["text_analyzer", "web_search"],
    }

    return specialization_tools.get(specialization, [])


def get_role_instructions(role: AgentRole) -> list[str]:
    """Get default instructions for a specific role"""

    role_instructions = {
        AgentRole.ASSISTANT: [
            "Você é um assistente virtual prestativo e amigável.",
            "Responda de forma clara e concisa.",
            "Sempre mantenha um tom profissional e cordial.",
        ],
        AgentRole.RESEARCHER: [
            "Você é um pesquisador especializado em coletar e analisar informações.",
            "Use ferramentas de busca para encontrar informações relevantes.",
            "Cite sempre as fontes das informações apresentadas.",
            "Organize as informações de forma clara e estruturada.",
        ],
        AgentRole.ANALYST: [
            "Você é um analista que processa e interpreta dados e informações.",
            "Analise os dados fornecidos de forma crítica.",
            "Forneça insights e recomendações baseadas em evidências.",
            "Apresente conclusões de forma clara e justificada.",
        ],
        AgentRole.CUSTOMER_SERVICE: [
            "Você é um atendente de customer service prestativo e empático.",
            "Escute atentamente as necessidades do cliente.",
            "Resolva problemas de forma eficiente e cordial.",
            "Mantenha sempre um tom profissional e amigável.",
        ],
        AgentRole.SALES: [
            "Você é um vendedor experiente e persuasivo.",
            "Identifique as necessidades do cliente antes de apresentar soluções.",
            "Seja honesto sobre produtos e serviços.",
            "Foque em criar valor para o cliente.",
        ],
    }

    return role_instructions.get(role, ["Você é um agente virtual prestativo."])
