#!/usr/bin/env python3
"""
CLAUDE.md Analyzer

Analyzes detector output, assigns confidence scores, identifies affected CLAUDE.md files,
and prioritizes recommendations by impact and certainty.
"""

import argparse
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path


@dataclass
class AnalyzedFinding:
    """Finding with analysis and priority"""
    finding_id: str
    type: str  # new_pattern, violation, staleness, anti_pattern
    category: str
    severity: str
    confidence: float
    priority: float  # Overall priority (0-100)
    title: str
    rationale: str
    affected_files: List[str]
    evidence_count: int
    recommendation_type: str  # add_section, modify_section, remove_section, update_example


class FindingAnalyzer:
    """Analyzes findings and generates analysis with recommendations"""

    def __init__(self, findings_json: Dict):
        self.findings_raw = findings_json.get('findings', [])
        self.analyzed_findings: List[AnalyzedFinding] = []

    def analyze(self) -> List[AnalyzedFinding]:
        """Analyze all findings and prioritize"""
        for i, finding in enumerate(self.findings_raw):
            analyzed = self._analyze_finding(finding, i)
            self.analyzed_findings.append(analyzed)

        # Sort by priority (highest first)
        self.analyzed_findings.sort(key=lambda f: f.priority, reverse=True)
        return self.analyzed_findings

    def _analyze_finding(self, finding: Dict, index: int) -> AnalyzedFinding:
        """Analyze a single finding"""
        finding_type = finding.get('type')
        category = finding.get('category')
        confidence = finding.get('confidence', 50)
        severity = finding.get('severity', 'low')
        evidence = finding.get('evidence', [])

        # Calculate priority based on severity + confidence + evidence
        severity_score = {
            'critical': 100,
            'high': 75,
            'medium': 50,
            'low': 25
        }.get(severity, 25)

        evidence_score = min(len(evidence) * 10, 100)  # Max 100 for evidence
        priority = (severity_score * 0.5 + confidence * 0.3 + evidence_score * 0.2)

        # Determine recommendation type
        recommendation_type = self._get_recommendation_type(finding_type, category)

        # Generate finding ID
        finding_id = f"{finding_type}_{category}_{index}"

        return AnalyzedFinding(
            finding_id=finding_id,
            type=finding_type,
            category=category,
            severity=severity,
            confidence=confidence,
            priority=priority,
            title=finding.get('title', 'Unknown Finding'),
            rationale=finding.get('rationale', ''),
            affected_files=finding.get('affected_files', []),
            evidence_count=len(evidence),
            recommendation_type=recommendation_type
        )

    def _get_recommendation_type(self, finding_type: str, category: str) -> str:
        """Determine what type of CLAUDE.md update is needed"""
        if finding_type == "violation":
            return "add_anti_pattern_section"
        elif finding_type == "anti_pattern":
            return "add_anti_pattern_section"
        elif finding_type == "new_pattern":
            return "add_pattern_section"
        elif finding_type == "staleness":
            return "remove_section"
        else:
            return "update_section"

    def get_high_priority_findings(self, min_priority: float = 70) -> List[AnalyzedFinding]:
        """Get findings above priority threshold"""
        return [f for f in self.analyzed_findings if f.priority >= min_priority]

    def get_by_file(self) -> Dict[str, List[AnalyzedFinding]]:
        """Group findings by affected CLAUDE.md file"""
        by_file = {}
        for finding in self.analyzed_findings:
            for file in finding.affected_files:
                if file not in by_file:
                    by_file[file] = []
                by_file[file].append(finding)
        return by_file

    def generate_summary(self) -> Dict:
        """Generate summary analysis"""
        total = len(self.analyzed_findings)
        high_priority = len(self.get_high_priority_findings())
        by_type = {}
        by_severity = {}

        for finding in self.analyzed_findings:
            # Count by type
            if finding.type not in by_type:
                by_type[finding.type] = 0
            by_type[finding.type] += 1

            # Count by severity
            if finding.severity not in by_severity:
                by_severity[finding.severity] = 0
            by_severity[finding.severity] += 1

        return {
            "total_findings": total,
            "high_priority_findings": high_priority,
            "findings_by_type": by_type,
            "findings_by_severity": by_severity,
            "affected_files": list(self.get_by_file().keys())
        }


def main():
    parser = argparse.ArgumentParser(
        description="Analyze detector findings and prioritize recommendations"
    )
    parser.add_argument("detector_output", help="Path to detector output JSON file")
    parser.add_argument("--min-priority", type=float, default=70,
                       help="Minimum priority threshold for recommendations (default: 70)")
    parser.add_argument("--output", help="Output JSON file (default: stdout)")

    args = parser.parse_args()

    # Load detector output
    with open(args.detector_output, 'r') as f:
        detector_output = json.load(f)

    # Analyze findings
    analyzer = FindingAnalyzer(detector_output)
    analyzed = analyzer.analyze()

    # Get high-priority findings
    high_priority = analyzer.get_high_priority_findings(args.min_priority)

    # Group by file
    by_file = analyzer.get_by_file()

    # Generate summary
    summary = analyzer.generate_summary()

    output = {
        "timestamp": datetime.now().isoformat(),
        "summary": summary,
        "high_priority_findings": [asdict(f) for f in high_priority],
        "all_findings": [asdict(f) for f in analyzed],
        "findings_by_file": {
            file: [asdict(f) for f in findings]
            for file, findings in by_file.items()
        }
    }

    if args.output:
        with open(args.output, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"✅ Analysis saved to {args.output}")
        print(f"\n📊 Summary:")
        print(f"   Total findings: {summary['total_findings']}")
        print(f"   High priority: {summary['high_priority_findings']}")
        print(f"   Affected files: {', '.join(summary['affected_files'])}")
    else:
        print(json.dumps(output, indent=2))

    return 0


if __name__ == "__main__":
    exit(main())
