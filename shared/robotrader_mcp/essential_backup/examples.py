"""
Tool Examples Schema for Robo-Trader MCP Tools.

Defines structure for tool usage examples following Anthropic's guidance
for 1-5 concrete examples per tool to improve agent success rates.
"""

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class ExampleComplexity(Enum):
    """Complexity levels for tool examples."""
    MINIMAL = "minimal"      # Basic usage with required parameters only
    COMMON = "common"        # Typical real-world scenarios
    ADVANCED = "advanced"    # Complex parameter combinations and edge cases


class ExampleCategory(Enum):
    """Categories for different use cases."""
    DEBUGGING = "debugging"      # Error analysis and troubleshooting
    MONITORING = "monitoring"    # System health and performance checks
    ANALYSIS = "analysis"        # Data analysis and insights
    DEVELOPMENT = "development"  # Development and testing workflows
    PRODUCTION = "production"    # Production operations and maintenance


class ToolExample(BaseModel):
    """Comprehensive example for a tool usage."""
    name: str = Field(..., description="Descriptive name for the example")
    description: str = Field(..., description="What this example demonstrates")
    complexity: ExampleComplexity = Field(..., description="Complexity level")
    category: ExampleCategory = Field(..., description="Use case category")

    # Input specification
    input_parameters: Dict[str, Any] = Field(..., description="Example input parameters")
    input_context: Optional[Dict[str, Any]] = Field(None, description="Example caller context")

    # Expected output
    expected_output: Dict[str, Any] = Field(..., description="Expected tool output structure")
    output_highlights: List[str] = Field(..., description="Key points in the expected output")

    # Usage guidance
    use_case: str = Field(..., description="Specific scenario where this example applies")
    best_practices: List[str] = Field(..., description="Tips for using this pattern effectively")
    common_pitfalls: List[str] = Field(default_factory=list, description="Common mistakes to avoid")

    # Success criteria
    success_indicators: List[str] = Field(..., description="What indicates the example worked correctly")
    performance_notes: Optional[str] = Field(None, description="Performance characteristics or expectations")


class ExamplesRegistry(BaseModel):
    """Registry containing examples for all tools."""
    tool_examples: Dict[str, List[ToolExample]] = Field(..., description="Examples organized by tool name")

    def get_examples_for_tool(self, tool_name: str) -> List[ToolExample]:
        """Get all examples for a specific tool."""
        return self.tool_examples.get(tool_name, [])

    def get_examples_by_category(self, category: ExampleCategory) -> List[tuple[str, ToolExample]]:
        """Get examples across all tools filtered by category."""
        results = []
        for tool_name, examples in self.tool_examples.items():
            for example in examples:
                if example.category == category:
                    results.append((tool_name, example))
        return results

    def get_minimal_examples(self, tool_name: str) -> List[ToolExample]:
        """Get only minimal complexity examples for quick start."""
        return [ex for ex in self.get_examples_for_tool(tool_name)
                if ex.complexity == ExampleComplexity.MINIMAL]

    def get_contextual_examples(self, tool_name: str, context: Dict[str, Any]) -> List[ToolExample]:
        """Get examples matching specific context requirements."""
        matching_examples = []
        tool_examples = self.get_examples_for_tool(tool_name)

        for example in tool_examples:
            if example.input_context:
                # Simple context matching - can be enhanced with fuzzy matching
                if all(k in context and context[k] == v
                      for k, v in example.input_context.items()):
                    matching_examples.append(example)
            else:
                # Include examples without strict context requirements
                matching_examples.append(example)

        return matching_examples