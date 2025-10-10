from typing import Dict, Any, Optional, List
import json
from datetime import datetime, timezone


class WebSocketDiffer:
    """
    Implements differential updates for WebSocket communication.

    Compares current and previous data states to send only changed fields,
    significantly reducing bandwidth and improving performance.
    """

    @staticmethod
    def compute_diff(previous: Optional[Dict[str, Any]], current: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compute differential update between previous and current state.

        Returns:
            - If no previous state: full update
            - If data unchanged: empty diff
            - Otherwise: only changed fields
        """
        if previous is None:
            return {"type": "full_update", "data": current, "timestamp": datetime.now(timezone.utc).isoformat()}

        diff = {}
        changed = False

        for key, current_value in current.items():
            previous_value = previous.get(key)

            if isinstance(current_value, dict) and isinstance(previous_value, dict):
                nested_diff = WebSocketDiffer._diff_dict(previous_value, current_value)
                if nested_diff:
                    diff[key] = nested_diff
                    changed = True
            elif isinstance(current_value, list) and isinstance(previous_value, list):
                if not WebSocketDiffer._lists_equal(previous_value, current_value):
                    diff[key] = current_value
                    changed = True
            elif current_value != previous_value:
                diff[key] = current_value
                changed = True

        for key in previous:
            if key not in current:
                diff[key] = None
                changed = True

        if not changed:
            return {}

        return {
            "type": "partial_update",
            "changes": diff,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    @staticmethod
    def _diff_dict(previous: Dict, current: Dict) -> Optional[Dict]:
        """Recursively diff nested dictionaries."""
        diff = {}
        changed = False

        for key, current_value in current.items():
            previous_value = previous.get(key)

            if isinstance(current_value, dict) and isinstance(previous_value, dict):
                nested_diff = WebSocketDiffer._diff_dict(previous_value, current_value)
                if nested_diff:
                    diff[key] = nested_diff
                    changed = True
            elif isinstance(current_value, list) and isinstance(previous_value, list):
                if not WebSocketDiffer._lists_equal(previous_value, current_value):
                    diff[key] = current_value
                    changed = True
            elif current_value != previous_value:
                diff[key] = current_value
                changed = True

        for key in previous:
            if key not in current:
                diff[key] = None
                changed = True

        return diff if changed else None

    @staticmethod
    def _lists_equal(list1: List, list2: List) -> bool:
        """Compare two lists for equality with proper serialization."""
        try:
            return json.dumps(list1, sort_keys=True, default=str) == json.dumps(list2, sort_keys=True, default=str)
        except (TypeError, ValueError):
            return list1 == list2

    @staticmethod
    def apply_diff(base: Dict[str, Any], diff: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply differential update to base state.

        Used by clients to reconstruct full state from partial updates.
        """
        if diff.get("type") == "full_update":
            return diff["data"]

        if diff.get("type") == "partial_update":
            result = base.copy()
            changes = diff.get("changes", {})

            for key, value in changes.items():
                if value is None:
                    result.pop(key, None)
                elif isinstance(value, dict) and isinstance(result.get(key), dict):
                    result[key] = WebSocketDiffer._merge_dict(result[key], value)
                else:
                    result[key] = value

            return result

        return base

    @staticmethod
    def _merge_dict(base: Dict, update: Dict) -> Dict:
        """Recursively merge update into base dictionary."""
        result = base.copy()

        for key, value in update.items():
            if value is None:
                result.pop(key, None)
            elif isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = WebSocketDiffer._merge_dict(result[key], value)
            else:
                result[key] = value

        return result
