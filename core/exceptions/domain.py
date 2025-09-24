"""Domain-specific exceptions"""

from core.exceptions import CustomException


class DomainException(CustomException):
    """Base domain exception"""


class AgentException(DomainException):
    """Agent-related exceptions"""


class AgentNotFound(AgentException):
    code = 404
    error_code = "AGENT_NOT_FOUND"
    message = "Agent not found"


class AgentAlreadyExists(AgentException):
    code = 409
    error_code = "AGENT_ALREADY_EXISTS"
    message = "Agent with this phone number already exists"


class CustomerException(DomainException):
    """Customer-related exceptions"""


class CustomerNotFound(CustomerException):
    code = 404
    error_code = "CUSTOMER_NOT_FOUND"
    message = "Customer not found"


class CustomerAlreadyExists(CustomerException):
    code = 409
    error_code = "CUSTOMER_ALREADY_EXISTS"
    message = "Customer with this phone number already exists"


class AgentConfigException(DomainException):
    """Agent configuration-related exceptions"""


class AgentConfigNotFound(AgentConfigException):
    code = 404
    error_code = "AGENT_CONFIG_NOT_FOUND"
    message = "Agent configuration not found"


class AgentConfigAlreadyExists(AgentConfigException):
    code = 409
    error_code = "AGENT_CONFIG_ALREADY_EXISTS"
    message = "Agent configuration already exists for this agent"
