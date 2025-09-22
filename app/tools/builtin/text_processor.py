"""
Text processing tools for agents
"""

import re
from typing import Dict, Any
from app.tools.base import (
    AgentTool,
    ToolResult,
    ToolStatus,
    ToolDefinition,
    ToolParameter,
)


class TextSummarizerTool(AgentTool):
    """Simple text summarization tool"""

    def __init__(self):
        super().__init__(
            name="text_summarizer",
            description="Summarize text by extracting key sentences",
            category="text_processing",
        )

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        text = parameters.get("text", "")
        max_sentences = parameters.get("max_sentences", 3)

        if not text:
            return ToolResult(
                status=ToolStatus.ERROR, error="Text parameter is required"
            )

        try:
            # Simple extractive summarization
            sentences = re.split(r"[.!?]+", text)
            sentences = [s.strip() for s in sentences if s.strip()]

            if len(sentences) <= max_sentences:
                summary = text
            else:
                # Take first, middle, and last sentences as a simple summary
                indices = [0, len(sentences) // 2, len(sentences) - 1]
                if max_sentences > 3:
                    # Add more evenly distributed sentences
                    step = len(sentences) // max_sentences
                    indices = list(range(0, len(sentences), step))[:max_sentences]

                summary_sentences = [
                    sentences[i] for i in indices if i < len(sentences)
                ]
                summary = ". ".join(summary_sentences) + "."

            result = {
                "original_length": len(text),
                "summary_length": len(summary),
                "original_sentences": len(sentences),
                "summary_sentences": len(summary_sentences)
                if "summary_sentences" in locals()
                else len(sentences),
                "summary": summary,
            }

            return ToolResult(status=ToolStatus.SUCCESS, data=result)

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR, error=f"Summarization failed: {str(e)}"
            )

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters=[
                ToolParameter(
                    name="text",
                    type="string",
                    description="Text to summarize",
                    required=True,
                ),
                ToolParameter(
                    name="max_sentences",
                    type="number",
                    description="Maximum number of sentences in summary",
                    required=False,
                    default=3,
                ),
            ],
        )


class TextAnalyzerTool(AgentTool):
    """Analyze text for basic metrics"""

    def __init__(self):
        super().__init__(
            name="text_analyzer",
            description="Analyze text for word count, readability, and other metrics",
            category="text_processing",
        )

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        text = parameters.get("text", "")

        if not text:
            return ToolResult(
                status=ToolStatus.ERROR, error="Text parameter is required"
            )

        try:
            # Basic text analysis
            words = re.findall(r"\b\w+\b", text.lower())
            sentences = re.split(r"[.!?]+", text)
            sentences = [s.strip() for s in sentences if s.strip()]
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

            # Word frequency
            word_freq = {}
            for word in words:
                word_freq[word] = word_freq.get(word, 0) + 1

            # Most common words (excluding very short words)
            common_words = sorted(
                [(word, freq) for word, freq in word_freq.items() if len(word) > 3],
                key=lambda x: x[1],
                reverse=True,
            )[:10]

            result = {
                "character_count": len(text),
                "word_count": len(words),
                "sentence_count": len(sentences),
                "paragraph_count": len(paragraphs),
                "avg_words_per_sentence": len(words) / len(sentences)
                if sentences
                else 0,
                "avg_chars_per_word": len(text) / len(words) if words else 0,
                "unique_words": len(word_freq),
                "most_common_words": common_words,
            }

            return ToolResult(status=ToolStatus.SUCCESS, data=result)

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR, error=f"Text analysis failed: {str(e)}"
            )

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters=[
                ToolParameter(
                    name="text",
                    type="string",
                    description="Text to analyze",
                    required=True,
                )
            ],
        )
