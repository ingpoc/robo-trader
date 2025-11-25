#!/usr/bin/env python3
"""
CLAUDE.md Recommendation Generator

Converts analyzed findings into specific CLAUDE.md update proposals with markdown diffs,
evidence references, and human-readable rationale.
"""

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List


@dataclass
class Recommendation:
    """A specific CLAUDE.md update recommendation"""
    recommendation_id: str
    file: str  # Which CLAUDE.md to update
    section: str  # Which section to add/modify/remove
    type: str  # add_section, modify_section, remove_section, update_example
    confidence: float  # 0-100
    priority: float  # 0-100
    title: str
    evidence: List[Dict]  # File:line references
    rationale: str
    proposed_diff: str  # Markdown diff
    related_sections: List[str]  # Other sections that might be affected


class RecommendationGenerator:
    """Generates CLAUDE.md update recommendations"""

    def __init__(self, analysis_json: Dict):
        self.high_priority = analysis_json.get('high_priority_findings', [])
        self.all_findings = analysis_json.get('all_findings', [])
        self.recommendations: List[Recommendation] = []

    def generate(self) -> List[Recommendation]:
        """Generate recommendations from analyzed findings"""
        for i, finding in enumerate(self.high_priority):
            rec = self._generate_recommendation(finding, i)
            self.recommendations.append(rec)
        return self.recommendations

    def _generate_recommendation(self, finding: Dict, index: int) -> Recommendation:
        """Generate a single recommendation"""
        finding_id = finding.get('finding_id', f'finding_{index}')
        finding_type = finding.get('type')
        category = finding.get('category')
        affected_files = finding.get('affected_files', [])
        evidence = finding.get('evidence', []) if isinstance(finding.get('evidence'), list) else []
        confidence = finding.get('confidence', 50)
        priority = finding.get('priority', 50)
        title = finding.get('title', '')
        rationale = finding.get('rationale', '')

        # Primary affected file
        primary_file = affected_files[0] if affected_files else 'CLAUDE.md'

        # Determine section and proposed diff
        if finding_type == "violation":
            section = "Anti-Patterns"
            diff = self._generate_violation_diff(category, evidence)
            related = self._get_related_sections(primary_file, "violations")
        elif finding_type == "anti_pattern":
            section = "Anti-Patterns"
            diff = self._generate_anti_pattern_diff(category, evidence)
            related = self._get_related_sections(primary_file, "anti_patterns")
        elif finding_type == "new_pattern":
            section = "Architecture Patterns" if "pattern" in category else "Code Patterns"
            diff = self._generate_pattern_diff(category, evidence)
            related = self._get_related_sections(primary_file, "patterns")
        else:
            section = "General"
            diff = self._generate_general_diff(category, evidence)
            related = []

        rec_id = f"{finding_type}_{category}_{index}"

        return Recommendation(
            recommendation_id=rec_id,
            file=primary_file,
            section=section,
            type=finding.get('recommendation_type', 'update_section'),
            confidence=confidence,
            priority=priority,
            title=title,
            evidence=evidence,
            rationale=rationale,
            proposed_diff=diff,
            related_sections=related
        )

    def _generate_violation_diff(self, category: str, evidence: List[Dict]) -> str:
        """Generate diff for a violation"""
        if category == "database_access":
            return """## Anti-Patterns

### ❌ DON'T: Direct Database Access
```python
# Blocks all operations during long-running processes
database = await container.get("database")
await database.connection.execute(...)
await database.connection.commit()
```

### ✅ DO: Use Locked State Methods
```python
# Use ConfigurationState's locked access
config_state = await container.get("configuration_state")
success = await config_state.store_analysis_history(symbol, timestamp, data)
success = await config_state.store_recommendation(symbol, rec_type, score, reasoning)
```

**Why**: Direct connection access bypasses ConfigurationState's `asyncio.Lock()`, causing database contention. Pages freeze during 30+ second analysis operations."""

        elif category == "sdk_usage":
            return """## Critical Rules

- **SDK Only**: All AI functionality must use Claude Agent SDK only. NO direct Anthropic API calls.
- **Client Manager**: Use `ClaudeSDKClientManager` singleton for all Claude interactions
- **Timeout Protection**: Wrap all Claude calls with `await query_with_timeout(client, prompt, timeout=60.0)`"""

        elif category == "async_usage":
            return """## Async-First Design (MANDATORY)

- **All I/O is non-blocking**: Use `async/await`
- **No time.sleep()**: Blocks ALL async operations. Use `await asyncio.sleep()` instead
- **Timeout protection**: All async operations have cancellation handling via `asyncio.wait_for()`"""

        else:
            return f"""## Update Needed for {category.replace('_', ' ').title()}

Add appropriate documentation based on usage patterns found in codebase."""

    def _generate_anti_pattern_diff(self, category: str, evidence: List[Dict]) -> str:
        """Generate diff for an anti-pattern"""
        if category == "async_usage":
            return """## Anti-Patterns

### ❌ DON'T: Use time.sleep() in Async Code
```python
async def process_items():
    for item in items:
        time.sleep(1)  # BLOCKS ALL ASYNC OPERATIONS!
```

### ✅ DO: Use Async-Safe Sleep or Polling
```python
# Option 1: Async sleep
async def process_items():
    for item in items:
        await asyncio.sleep(1)  # Non-blocking

# Option 2: Condition polling
while not condition_met:
    await asyncio.sleep(0.1)  # Poll with small delays
```

**Why**: `time.sleep()` blocks the entire event loop, preventing other async operations from running. This freezes the entire system."""

        elif category == "modularization":
            return """## Modularization (ENFORCED)

- **Max 350 lines per file**: Split larger files into focused modules
- **Max 10 methods per class**: Break up classes with too many responsibilities
- **Single responsibility**: Each file should have one clear purpose"""

        else:
            return f"""## Anti-Pattern Found: {category.replace('_', ' ').title()}

Add documentation to prevent repeated mistakes."""

    def _generate_pattern_diff(self, category: str, evidence: List[Dict]) -> str:
        """Generate diff for a new pattern"""
        if category == "queue_handler":
            return """## Sequential Queue Architecture (CRITICAL)

### Handler Examples
**Documented Handlers**:
- `RECOMMENDATION_GENERATION` - AI analysis task
- `PORTFOLIO_SYNC` - Portfolio update task
- `DATA_FETCH` - Market data task
- `EARNINGS_FETCH` - Earnings data task
- `NEWS_FETCH` - News data task
- `SIGNAL_CALCULATION` - Signal generation task
- `FORECAST_CALCULATION` - Forecast generation task

**Note**: New handlers should follow the same pattern and be added to this list."""

        elif category == "coordinator":
            return """## Coordinator Layer

### Documented Coordinators
- `SessionCoordinator` - Claude SDK session lifecycle
- `QueryCoordinator` - Query/request processing
- `TaskCoordinator` - Background task management
- `StatusCoordinator` - System status aggregation
- `BroadcastCoordinator` - Real-time UI updates
- `PortfolioCoordinator` - Portfolio operations

**Rule**: Each coordinator max 150 lines, single responsibility."""

        else:
            return f"""## New Pattern Detected: {category.replace('_', ' ').title()}

Document this pattern to guide future implementations."""

    def _generate_general_diff(self, category: str, evidence: List[Dict]) -> str:
        """Generate diff for general updates"""
        return f"""## Update for {category.replace('_', ' ').title()}

This section needs update based on codebase analysis."""

    def _get_related_sections(self, file: str, context: str) -> List[str]:
        """Get related sections that might also need updates"""
        mapping = {
            "src/CLAUDE.md": {
                "violations": ["Code Quality Standards", "Error Handling"],
                "anti_patterns": ["Common Issues & Quick Fixes"],
                "patterns": ["Architecture Patterns"]
            },
            "src/core/CLAUDE.md": {
                "violations": ["Critical Rules"],
                "anti_patterns": ["Anti-Patterns"],
                "patterns": ["Architecture Patterns"]
            },
            "src/web/CLAUDE.md": {
                "violations": ["Database Access", "Error Handling"],
                "anti_patterns": [],
                "patterns": ["API Patterns"]
            }
        }
        return mapping.get(file, {}).get(context, [])

    def to_markdown(self, recommendations: List[Recommendation]) -> str:
        """Convert recommendations to markdown report"""
        lines = [
            "# CLAUDE.md Update Recommendations\n",
            f"**Generated**: {datetime.now().isoformat()}\n",
            f"**Total Recommendations**: {len(recommendations)}\n",
            ""
        ]

        # Group by file
        by_file = {}
        for rec in recommendations:
            if rec.file not in by_file:
                by_file[rec.file] = []
            by_file[rec.file].append(rec)

        for file, recs in sorted(by_file.items()):
            lines.append(f"\n## {file}\n")
            for i, rec in enumerate(recs, 1):
                lines.append(f"### Recommendation {i}: {rec.title}")
                lines.append(f"**Confidence**: {rec.confidence:.0f}% | **Priority**: {rec.priority:.0f}%")
                lines.append(f"**Section**: {rec.section} | **Type**: {rec.type}\n")
                lines.append("**Evidence**:")
                for ev in rec.evidence[:3]:
                    lines.append(f"- `{ev.get('file', 'unknown')}:{ev.get('line', '?')}` - {ev.get('snippet', '')}")
                lines.append(f"\n**Rationale**: {rec.rationale}\n")
                lines.append("**Proposed Diff**:")
                lines.append("```markdown")
                lines.append(rec.proposed_diff)
                lines.append("```\n")
                if rec.related_sections:
                    lines.append(f"**Related Sections**: {', '.join(rec.related_sections)}\n")

        return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate CLAUDE.md update recommendations"
    )
    parser.add_argument("analysis_output", help="Path to analyzer output JSON file")
    parser.add_argument("--output-format", choices=["json", "markdown"],
                       default="markdown", help="Output format")
    parser.add_argument("--output", help="Output file (default: stdout)")

    args = parser.parse_args()

    # Load analysis output
    with open(args.analysis_output, 'r') as f:
        analysis = json.load(f)

    # Generate recommendations
    generator = RecommendationGenerator(analysis)
    recommendations = generator.generate()

    if args.output_format == "json":
        output = {
            "timestamp": datetime.now().isoformat(),
            "total_recommendations": len(recommendations),
            "recommendations": [asdict(r) for r in recommendations]
        }
        output_text = json.dumps(output, indent=2)
    else:  # markdown
        output_text = generator.to_markdown(recommendations)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output_text)
        print(f"✅ Recommendations saved to {args.output}")
        print(f"   Total recommendations: {len(recommendations)}")
    else:
        print(output_text)

    return 0


if __name__ == "__main__":
    exit(main())
