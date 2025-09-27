class AIRouter:
    """Route tasks to the best AI model"""

    MODEL_ROUTING = {
        "simple": ("gpt-5-nano", 0.3),
        "complex": ("gpt-5", 0.7),
        "creative": ("gpt-5", 0.9),
        "analysis": ("gpt-5", 0.1),
    }

    @classmethod
    def get_model_for_task(cls, task_type: str, text_length: int = 0):
        """Smart model selection based on task and complexity"""
        # Route based on text length
        if text_length > 50000:
            return ("gpt-5", 0.3)  # Better for long texts
        # Route based on task type
        return cls.MODEL_ROUTING.get(task_type, ("gpt-5-nano", 0.5))
