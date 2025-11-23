#!/usr/bin/env python3
"""
CLAUDE.md Recommendation Validator

Validates recommendations before proposing them:
- Checks for conflicting rules across CLAUDE.md files
- Verifies examples in recommendations work
- Confirms referenced files still exist
- Performs impact analysis
"""

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class ValidationResult:
    """Result of validating a recommendation"""
    recommendation_id: str
    is_valid: bool
    conflicts: List[str]
    broken_references: List[str]
    example_issues: List[str]
    impact_score: float  # 0-100, higher = more impactful
    issues: List[str]


class RecommendationValidator:
    """Validates recommendations for safety and accuracy"""

    def __init__(self, recommendations: List[Dict], project_root: Path = None):
        self.recommendations = recommendations
        self.project_root = project_root or Path(".")
        self.claude_md_files = self._find_claude_md_files()
        self.validation_results: List[ValidationResult] = []

    def _find_claude_md_files(self) -> Dict[str, str]:
        """Load all CLAUDE.md files and their content"""
        claude_files = {}
        for file_path in self.project_root.glob("**/CLAUDE.md"):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    claude_files[str(file_path.relative_to(self.project_root))] = f.read()
            except Exception:
                pass
        return claude_files

    def validate_all(self) -> List[ValidationResult]:
        """Validate all recommendations"""
        for i, rec in enumerate(self.recommendations):
            result = self._validate_single(rec, i)
            self.validation_results.append(result)
        return self.validation_results

    def _validate_single(self, rec: Dict, index: int) -> ValidationResult:
        """Validate a single recommendation"""
        rec_id = rec.get('recommendation_id', f'rec_{index}')
        issues = []
        conflicts = []
        broken_refs = []
        example_issues = []

        # 1. Check for conflicting rules
        conflicts = self._check_conflicts(rec)
        if conflicts:
            issues.extend(conflicts)

        # 2. Check for broken references
        broken_refs = self._check_broken_references(rec)
        if broken_refs:
            issues.extend(broken_refs)

        # 3. Validate code examples
        example_issues = self._validate_examples(rec)
        if example_issues:
            issues.extend(example_issues)

        # 4. Calculate impact score
        impact_score = self._calculate_impact(rec)

        is_valid = len(issues) == 0

        return ValidationResult(
            recommendation_id=rec_id,
            is_valid=is_valid,
            conflicts=conflicts,
            broken_references=broken_refs,
            example_issues=example_issues,
            impact_score=impact_score,
            issues=issues
        )

    def _check_conflicts(self, rec: Dict) -> List[str]:
        """Check for conflicting rules across CLAUDE.md files"""
        conflicts = []
        proposed_diff = rec.get('proposed_diff', '')
        affected_files = rec.get('affected_files', [])

        # Extract potential rules from diff
        rule_pattern = r'(?:###?\s+)?(\w[\w\s]*?):\s*(.+?)(?:\n|$)'
        rules = re.findall(rule_pattern, proposed_diff)

        # Check each rule against existing files
        for rule_name, rule_content in rules:
            for file_path, file_content in self.claude_md_files.items():
                # Skip the file being updated
                if file_path in affected_files:
                    continue

                # Check if rule already exists
                if rule_name.lower() in file_content.lower():
                    # Check if content conflicts
                    if rule_content.lower() not in file_content.lower():
                        conflicts.append(
                            f"Rule '{rule_name}' already exists in {file_path} with different content"
                        )

        return conflicts

    def _check_broken_references(self, rec: Dict) -> List[str]:
        """Check for broken file/section references"""
        broken = []
        proposed_diff = rec.get('proposed_diff', '')

        # Look for file path references: `src/...`
        file_refs = re.findall(r'`(src/[\w/\.]+)`', proposed_diff)
        for file_ref in file_refs:
            if not (self.project_root / file_ref).exists():
                broken.append(f"File reference broken: {file_ref}")

        # Look for section references: #section-name
        section_refs = re.findall(r'\[.*?\]\(#([\w-]+)\)', proposed_diff)
        target_file = rec.get('file', '')
        if target_file in self.claude_md_files:
            content = self.claude_md_files[target_file]
            for section in section_refs:
                # Convert section ID to heading format
                heading = section.replace('-', ' ').title()
                if heading.lower() not in content.lower():
                    broken.append(f"Section reference broken: #{section}")

        return broken

    def _validate_examples(self, rec: Dict) -> List[str]:
        """Validate code examples in recommendations"""
        issues = []
        proposed_diff = rec.get('proposed_diff', '')

        # Extract code blocks
        python_blocks = re.findall(r'```python\n(.*?)\n```', proposed_diff, re.DOTALL)
        typescript_blocks = re.findall(r'```typescript\n(.*?)\n```', proposed_diff, re.DOTALL)

        # Basic syntax validation
        for block in python_blocks:
            if not self._is_valid_python_syntax(block):
                issues.append("Invalid Python syntax in code example")

        for block in typescript_blocks:
            if not self._is_valid_typescript_syntax(block):
                issues.append("Invalid TypeScript syntax in code example")

        return issues

    def _is_valid_python_syntax(self, code: str) -> bool:
        """Check if Python code is valid"""
        try:
            import ast
            ast.parse(code)
            return True
        except:
            return False

    def _is_valid_typescript_syntax(self, code: str) -> bool:
        """Basic TypeScript syntax validation (limited)"""
        # Simple check: balanced braces/brackets
        braces = code.count('{') == code.count('}')
        brackets = code.count('[') == code.count(']')
        return braces and brackets

    def _calculate_impact(self, rec: Dict) -> float:
        """Calculate impact score (0-100)"""
        score = 50  # Base score

        # Increase for critical severity
        if rec.get('severity') == 'critical':
            score += 25
        elif rec.get('severity') == 'high':
            score += 15

        # Increase for high confidence
        confidence = rec.get('confidence', 50)
        score += (confidence - 50) * 0.2  # Max ±10 points

        # Increase for multiple affected files
        affected = len(rec.get('affected_files', []))
        score += min(affected * 5, 15)

        return min(score, 100)

    def get_valid_recommendations(self) -> List[Dict]:
        """Get only valid recommendations"""
        valid_indices = {
            i for i, result in enumerate(self.validation_results)
            if result.is_valid
        }
        return [rec for i, rec in enumerate(self.recommendations) if i in valid_indices]

    def generate_report(self) -> Dict:
        """Generate validation report"""
        total = len(self.validation_results)
        valid = sum(1 for r in self.validation_results if r.is_valid)
        invalid = total - valid

        return {
            "timestamp": str(__import__('datetime').datetime.now().isoformat()),
            "total_recommendations": total,
            "valid_recommendations": valid,
            "invalid_recommendations": invalid,
            "results": [asdict(r) for r in self.validation_results]
        }


def main():
    parser = argparse.ArgumentParser(
        description="Validate CLAUDE.md update recommendations"
    )
    parser.add_argument("recommendations_json", help="Path to recommendations JSON file")
    parser.add_argument("--project-root", default=".", help="Project root path")
    parser.add_argument("--output", help="Output validation report (JSON)")

    args = parser.parse_args()

    # Load recommendations
    with open(args.recommendations_json, 'r') as f:
        data = json.load(f)
        recommendations = data.get('recommendations', [])

    # Validate
    validator = RecommendationValidator(recommendations, Path(args.project_root))
    validator.validate_all()

    # Generate report
    report = validator.generate_report()

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"✅ Validation report saved to {args.output}")
    else:
        print(json.dumps(report, indent=2))

    print(f"\n📊 Summary:")
    print(f"   Valid: {report['valid_recommendations']}")
    print(f"   Invalid: {report['invalid_recommendations']}")

    return 0 if report['invalid_recommendations'] == 0 else 1


if __name__ == "__main__":
    exit(main())
