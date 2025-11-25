#!/usr/bin/env python3
"""
CLAUDE.md Feedback Tracker

Records accepted/rejected recommendations and updates confidence scoring
based on feedback patterns to improve accuracy over time.
"""

import argparse
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Feedback:
    """User feedback on a recommendation"""
    recommendation_id: str
    accepted: bool
    notes: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FeedbackRecord:
    """Aggregated feedback for a recommendation pattern"""
    recommendation_id: str
    category: str
    type: str
    total_feedback_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    acceptance_rate: float = 0.0
    confidence_adjustment: float = 0.0
    last_feedback: Optional[str] = None


class FeedbackTracker:
    """Tracks recommendation feedback and learns from it"""

    def __init__(self, feedback_db_path: Path = None):
        self.feedback_db_path = feedback_db_path or Path(".") / "claude_md_feedback.json"
        self.feedback_records: Dict[str, FeedbackRecord] = {}
        self.feedback_history: List[Feedback] = []
        self._load_feedback_db()

    def _load_feedback_db(self):
        """Load existing feedback database"""
        if self.feedback_db_path.exists():
            try:
                with open(self.feedback_db_path, 'r') as f:
                    data = json.load(f)
                    # Load records
                    for rec_id, record_data in data.get('records', {}).items():
                        self.feedback_records[rec_id] = FeedbackRecord(
                            recommendation_id=record_data['recommendation_id'],
                            category=record_data['category'],
                            type=record_data['type'],
                            total_feedback_count=record_data.get('total_feedback_count', 0),
                            accepted_count=record_data.get('accepted_count', 0),
                            rejected_count=record_data.get('rejected_count', 0),
                            acceptance_rate=record_data.get('acceptance_rate', 0.0),
                            confidence_adjustment=record_data.get('confidence_adjustment', 0.0),
                            last_feedback=record_data.get('last_feedback')
                        )
                    # Load history (limited to last 100 entries)
                    history_data = data.get('history', [])
                    for entry in history_data[-100:]:
                        self.feedback_history.append(Feedback(
                            recommendation_id=entry['recommendation_id'],
                            accepted=entry['accepted'],
                            notes=entry.get('notes'),
                            timestamp=entry['timestamp']
                        ))
            except Exception as e:
                print(f"Warning: Could not load feedback database: {e}")

    def record_feedback(self, rec_id: str, accepted: bool, notes: str = None,
                       category: str = None, rec_type: str = None) -> FeedbackRecord:
        """Record feedback on a recommendation"""
        feedback = Feedback(
            recommendation_id=rec_id,
            accepted=accepted,
            notes=notes
        )
        self.feedback_history.append(feedback)

        # Update or create record
        if rec_id not in self.feedback_records:
            self.feedback_records[rec_id] = FeedbackRecord(
                recommendation_id=rec_id,
                category=category or 'unknown',
                type=rec_type or 'unknown'
            )

        record = self.feedback_records[rec_id]
        record.total_feedback_count += 1
        if accepted:
            record.accepted_count += 1
        else:
            record.rejected_count += 1

        record.acceptance_rate = record.accepted_count / record.total_feedback_count
        record.last_feedback = feedback.timestamp

        # Calculate confidence adjustment
        # +5% per acceptance, -10% per rejection
        adjustment = (record.accepted_count * 5) - (record.rejected_count * 10)
        record.confidence_adjustment = max(-30, min(adjustment, 30))  # Clamp -30 to +30

        self._save_feedback_db()
        return record

    def get_confidence_adjustment(self, rec_id: str) -> float:
        """Get confidence adjustment for a recommendation"""
        if rec_id in self.feedback_records:
            return self.feedback_records[rec_id].confidence_adjustment
        return 0.0

    def get_category_stats(self, category: str) -> Dict:
        """Get statistics for all recommendations in a category"""
        matching = [r for r in self.feedback_records.values() if r.category == category]

        if not matching:
            return {
                "category": category,
                "total_recommendations": 0,
                "total_feedback": 0,
                "acceptance_rate": 0.0
            }

        total_feedback = sum(r.total_feedback_count for r in matching)
        total_accepted = sum(r.accepted_count for r in matching)
        acceptance_rate = total_accepted / total_feedback if total_feedback > 0 else 0.0

        return {
            "category": category,
            "total_recommendations": len(matching),
            "total_feedback": total_feedback,
            "total_accepted": total_accepted,
            "total_rejected": total_feedback - total_accepted,
            "acceptance_rate": acceptance_rate,
            "recommendations": [asdict(r) for r in matching]
        }

    def get_improvement_suggestions(self) -> List[str]:
        """Analyze feedback patterns and suggest improvements"""
        suggestions = []

        # Find low-accuracy categories
        categories = set(r.category for r in self.feedback_records.values())
        for cat in categories:
            stats = self.get_category_stats(cat)
            if stats['acceptance_rate'] < 0.5 and stats['total_feedback'] >= 5:
                suggestions.append(
                    f"Category '{cat}' has low acceptance rate ({stats['acceptance_rate']:.0%}). "
                    f"Review detection rules and consider stricter thresholds."
                )

        # Find high-accuracy categories
        for cat in categories:
            stats = self.get_category_stats(cat)
            if stats['acceptance_rate'] > 0.9 and stats['total_feedback'] >= 5:
                suggestions.append(
                    f"Category '{cat}' has high acceptance rate ({stats['acceptance_rate']:.0%}). "
                    f"Consider lowering confidence threshold to catch more patterns."
                )

        return suggestions

    def adjust_confidence(self, original_confidence: float, rec_id: str) -> float:
        """Adjust recommendation confidence based on feedback"""
        adjustment = self.get_confidence_adjustment(rec_id)
        adjusted = original_confidence + adjustment
        return max(0, min(100, adjusted))  # Clamp 0-100

    def _save_feedback_db(self):
        """Save feedback database to disk"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "records": {
                    rec_id: asdict(record)
                    for rec_id, record in self.feedback_records.items()
                },
                "history": [asdict(f) for f in self.feedback_history[-100:]]
            }
            self.feedback_db_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.feedback_db_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save feedback database: {e}")

    def export_learning_data(self, output_path: Path):
        """Export learning data for analysis"""
        learning_data = {
            "timestamp": datetime.now().isoformat(),
            "category_performance": {},
            "type_performance": {},
            "improvement_suggestions": self.get_improvement_suggestions(),
            "recommendations_data": []
        }

        # Category performance
        categories = set(r.category for r in self.feedback_records.values())
        for cat in categories:
            stats = self.get_category_stats(cat)
            learning_data['category_performance'][cat] = {
                "total_recommendations": stats['total_recommendations'],
                "total_feedback": stats['total_feedback'],
                "acceptance_rate": stats['acceptance_rate']
            }

        # Type performance
        types = set(r.type for r in self.feedback_records.values())
        for rec_type in types:
            matching = [r for r in self.feedback_records.values() if r.type == rec_type]
            total_feedback = sum(r.total_feedback_count for r in matching)
            total_accepted = sum(r.accepted_count for r in matching)
            acceptance_rate = total_accepted / total_feedback if total_feedback > 0 else 0.0
            learning_data['type_performance'][rec_type] = {
                "acceptance_rate": acceptance_rate,
                "total_feedback": total_feedback
            }

        # All recommendation data
        learning_data['recommendations_data'] = [
            asdict(r) for r in self.feedback_records.values()
        ]

        with open(output_path, 'w') as f:
            json.dump(learning_data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Track feedback on CLAUDE.md recommendations and learn from patterns"
    )
    parser.add_argument("command", choices=["record", "stats", "export", "adjust"],
                       help="Command to execute")
    parser.add_argument("--rec-id", help="Recommendation ID")
    parser.add_argument("--accepted", type=bool, default=True, help="Was recommendation accepted?")
    parser.add_argument("--notes", help="Feedback notes")
    parser.add_argument("--db", default="claude_md_feedback.json", help="Feedback database path")
    parser.add_argument("--category", help="Category for stats")
    parser.add_argument("--output", help="Output file")
    parser.add_argument("--confidence", type=float, help="Original confidence for adjustment")

    args = parser.parse_args()

    tracker = FeedbackTracker(Path(args.db))

    if args.command == "record":
        if not args.rec_id:
            print("Error: --rec-id required for record command")
            return 1
        record = tracker.record_feedback(
            args.rec_id,
            args.accepted,
            args.notes
        )
        print(f"✅ Feedback recorded for {args.rec_id}")
        print(f"   Acceptance rate: {record.acceptance_rate:.0%}")
        print(f"   Confidence adjustment: {record.confidence_adjustment:+.1f}%")
        return 0

    elif args.command == "stats":
        if args.category:
            stats = tracker.get_category_stats(args.category)
            print(json.dumps(stats, indent=2))
        else:
            # All stats
            all_stats = {
                "categories": {
                    cat: tracker.get_category_stats(cat)['acceptance_rate']
                    for cat in set(r.category for r in tracker.feedback_records.values())
                },
                "improvements": tracker.get_improvement_suggestions()
            }
            print(json.dumps(all_stats, indent=2))
        return 0

    elif args.command == "export":
        if not args.output:
            print("Error: --output required for export command")
            return 1
        tracker.export_learning_data(Path(args.output))
        print(f"✅ Learning data exported to {args.output}")
        return 0

    elif args.command == "adjust":
        if not args.rec_id or args.confidence is None:
            print("Error: --rec-id and --confidence required for adjust command")
            return 1
        adjusted = tracker.adjust_confidence(args.confidence, args.rec_id)
        print(f"Original confidence: {args.confidence:.1f}%")
        print(f"Adjusted confidence: {adjusted:.1f}%")
        return 0

    return 1


if __name__ == "__main__":
    exit(main())
