"""
Web search tool for agents
"""

import aiohttp
from typing import Dict, Any
from app.tools.base import (
    AgentTool,
    ToolResult,
    ToolStatus,
    ToolDefinition,
    ToolParameter,
)


class WebSearchTool(AgentTool):
    """Simple web search tool using DuckDuckGo Instant Answer API"""

    def __init__(self):
        super().__init__(
            name="web_search",
            description="Search the web for information using DuckDuckGo",
            category="information",
        )

    async def execute(self, parameters: Dict[str, Any]) -> ToolResult:
        query = parameters.get("query", "")
        max_results = parameters.get("max_results", 5)

        if not query:
            return ToolResult(
                status=ToolStatus.ERROR, error="Query parameter is required"
            )

        try:
            async with aiohttp.ClientSession() as session:
                # Using DuckDuckGo Instant Answer API
                url = "https://api.duckduckgo.com/"
                params = {
                    "q": query,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                }

                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Extract relevant information
                        results = {
                            "query": query,
                            "abstract": data.get("Abstract", ""),
                            "abstract_source": data.get("AbstractSource", ""),
                            "definition": data.get("Definition", ""),
                            "answer": data.get("Answer", ""),
                            "related_topics": [
                                {
                                    "text": topic.get("Text", ""),
                                    "url": topic.get("FirstURL", ""),
                                }
                                for topic in data.get("RelatedTopics", [])[:max_results]
                            ],
                        }

                        return ToolResult(status=ToolStatus.SUCCESS, data=results)
                    else:
                        return ToolResult(
                            status=ToolStatus.ERROR,
                            error=f"Search API returned status {response.status}",
                        )

        except Exception as e:
            return ToolResult(status=ToolStatus.ERROR, error=f"Search failed: {str(e)}")

    def get_definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.name,
            description=self.description,
            category=self.category,
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description="Search query",
                    required=True,
                ),
                ToolParameter(
                    name="max_results",
                    type="number",
                    description="Maximum number of results to return",
                    required=False,
                    default=5,
                ),
            ],
        )
