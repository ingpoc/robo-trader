"""
Feature Dependency Resolution Engine

Handles graph-based dependency management, conflict detection,
and cascade enable/disable logic for features.
"""

import hashlib
import json
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from .models import (DependencyResolutionResult, DependencyType, FeatureConfig,
                     FeatureDependency, FeatureState)


@dataclass
class DependencyGraph:
    """Represents the dependency graph of all features."""

    nodes: Set[str]  # Feature IDs
    edges: Dict[str, List[FeatureDependency]]  # feature_id -> dependencies
    reverse_edges: Dict[str, List[str]]  # feature_id -> dependents

    def __init__(self):
        self.nodes = set()
        self.edges = defaultdict(list)
        self.reverse_edges = defaultdict(list)

    def add_feature(
        self, feature_id: str, dependencies: List[FeatureDependency]
    ) -> None:
        """Add a feature and its dependencies to the graph."""
        self.nodes.add(feature_id)
        self.edges[feature_id] = dependencies

        # Build reverse edges
        for dep in dependencies:
            if dep.dependency_type == DependencyType.REQUIRES:
                self.reverse_edges[dep.feature_id].append(feature_id)

    def remove_feature(self, feature_id: str) -> None:
        """Remove a feature from the graph."""
        self.nodes.discard(feature_id)

        # Remove outgoing edges
        if feature_id in self.edges:
            for dep in self.edges[feature_id]:
                if dep.dependency_type == DependencyType.REQUIRES:
                    self.reverse_edges[dep.feature_id].remove(feature_id)
            del self.edges[feature_id]

        # Remove incoming edges
        if feature_id in self.reverse_edges:
            del self.reverse_edges[feature_id]

    def get_dependencies(self, feature_id: str) -> List[FeatureDependency]:
        """Get all dependencies for a feature."""
        return self.edges.get(feature_id, [])

    def get_dependents(self, feature_id: str) -> List[str]:
        """Get all features that depend on this feature."""
        return self.reverse_edges.get(feature_id, [])

    def has_cycle(self) -> bool:
        """Check if the dependency graph has cycles."""
        visited = set()
        rec_stack = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for dep in self.edges.get(node, []):
                if dep.dependency_type != DependencyType.REQUIRES:
                    continue

                dep_id = dep.feature_id
                if dep_id not in visited:
                    if dfs(dep_id):
                        return True
                elif dep_id in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node in self.nodes:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def find_cycles(self) -> List[List[str]]:
        """Find all cycles in the dependency graph."""
        cycles = []
        visited = set()
        rec_stack = set()
        path = []

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for dep in self.edges.get(node, []):
                if dep.dependency_type != DependencyType.REQUIRES:
                    continue

                dep_id = dep.feature_id
                if dep_id not in visited:
                    if dfs(dep_id):
                        return True
                elif dep_id in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(dep_id)
                    cycles.append(path[cycle_start:] + [dep_id])
                    return True

            rec_stack.remove(node)
            path.pop()
            return False

        for node in self.nodes:
            if node not in visited:
                dfs(node)

        return cycles


class DependencyResolver:
    """
    Resolves feature dependencies and determines enable/disable order.

    Provides graph-based dependency management with conflict detection,
    circular dependency detection, and cascade operations.
    """

    def __init__(self):
        self.graph = DependencyGraph()
        self.features: Dict[str, FeatureConfig] = {}
        self.states: Dict[str, FeatureState] = {}

    def update_graph(
        self, features: Dict[str, FeatureConfig], states: Dict[str, FeatureState]
    ) -> None:
        """Update the dependency graph with current features and states."""
        self.features = features
        self.states = states

        # Rebuild graph
        self.graph = DependencyGraph()
        for feature_id, config in features.items():
            self.graph.add_feature(feature_id, config.dependencies)

    async def resolve_enable_order(
        self, feature_ids: List[str], include_dependencies: bool = True
    ) -> DependencyResolutionResult:
        """
        Resolve the order in which features should be enabled.

        Args:
            feature_ids: List of feature IDs to enable
            include_dependencies: Whether to automatically include dependencies

        Returns:
            DependencyResolutionResult with resolved order and any issues
        """
        result = DependencyResolutionResult(success=True)

        try:
            # Check for cycles first
            cycles = self.graph.find_cycles()
            if cycles:
                result.success = False
                result.circular_dependencies = cycles
                result.warnings.append(f"Found {len(cycles)} circular dependencies")
                return result

            # Get all features to enable (including dependencies if requested)
            features_to_enable = set(feature_ids)
            if include_dependencies:
                for feature_id in feature_ids:
                    deps = self._get_all_dependencies(feature_id)
                    features_to_enable.update(deps)

            # Check for missing dependencies
            missing_deps = []
            for feature_id in features_to_enable:
                if feature_id not in self.features:
                    missing_deps.append(feature_id)

            if missing_deps:
                result.success = False
                result.missing_dependencies = missing_deps
                return result

            # Check for conflicts
            conflicts = self._check_conflicts(features_to_enable)
            if conflicts:
                result.conflicts = conflicts
                result.warnings.append(f"Found {len(conflicts)} conflicts")

            # Topological sort for enable order
            enable_order = self._topological_sort(features_to_enable)
            result.resolved_order = enable_order

            logger.info(
                f"Resolved enable order for {len(features_to_enable)} features: {enable_order}"
            )

        except Exception as e:
            logger.error(f"Failed to resolve enable order: {e}")
            result.success = False
            result.warnings.append(f"Resolution failed: {str(e)}")

        return result

    async def resolve_disable_order(
        self, feature_ids: List[str], cascade: bool = True
    ) -> DependencyResolutionResult:
        """
        Resolve the order in which features should be disabled.

        Args:
            feature_ids: List of feature IDs to disable
            cascade: Whether to cascade disable to dependents

        Returns:
            DependencyResolutionResult with resolved order and any issues
        """
        result = DependencyResolutionResult(success=True)

        try:
            # Get all features to disable (including dependents if cascading)
            features_to_disable = set(feature_ids)
            if cascade:
                for feature_id in feature_ids:
                    dependents = self._get_all_dependents(feature_id)
                    features_to_disable.update(dependents)

            # Reverse topological sort for disable order (dependents first)
            disable_order = self._reverse_topological_sort(features_to_disable)
            result.resolved_order = disable_order

            logger.info(
                f"Resolved disable order for {len(features_to_disable)} features: {disable_order}"
            )

        except Exception as e:
            logger.error(f"Failed to resolve disable order: {e}")
            result.success = False
            result.warnings.append(f"Resolution failed: {str(e)}")

        return result

    def _get_all_dependencies(
        self, feature_id: str, visited: Optional[Set[str]] = None
    ) -> Set[str]:
        """Get all transitive dependencies for a feature."""
        if visited is None:
            visited = set()

        if feature_id in visited or feature_id not in self.features:
            return visited

        visited.add(feature_id)

        for dep in self.graph.get_dependencies(feature_id):
            if dep.dependency_type == DependencyType.REQUIRES and not dep.optional:
                self._get_all_dependencies(dep.feature_id, visited)

        return visited

    def _get_all_dependents(
        self, feature_id: str, visited: Optional[Set[str]] = None
    ) -> Set[str]:
        """Get all transitive dependents for a feature."""
        if visited is None:
            visited = set()

        if feature_id in visited:
            return visited

        visited.add(feature_id)

        for dependent in self.graph.get_dependents(feature_id):
            self._get_all_dependents(dependent, visited)

        return visited

    def _check_conflicts(self, feature_ids: Set[str]) -> List[Dict[str, Any]]:
        """Check for conflicts between features."""
        conflicts = []

        for feature_id in feature_ids:
            if feature_id not in self.features:
                continue

            for dep in self.graph.get_dependencies(feature_id):
                if dep.dependency_type == DependencyType.CONFLICTS:
                    if dep.feature_id in feature_ids:
                        conflicts.append(
                            {
                                "feature": feature_id,
                                "conflicts_with": dep.feature_id,
                                "type": "direct_conflict",
                            }
                        )

        return conflicts

    def _topological_sort(self, feature_ids: Set[str]) -> List[str]:
        """Perform topological sort on the dependency graph."""
        in_degree = defaultdict(int)
        graph = defaultdict(list)

        # Build graph and calculate in-degrees
        for feature_id in feature_ids:
            for dep in self.graph.get_dependencies(feature_id):
                if (
                    dep.dependency_type == DependencyType.REQUIRES
                    and not dep.optional
                    and dep.feature_id in feature_ids
                ):
                    graph[dep.feature_id].append(feature_id)
                    in_degree[feature_id] += 1

        # Queue for nodes with no incoming edges
        queue = deque([node for node in feature_ids if in_degree[node] == 0])
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If we couldn't process all nodes, there's a cycle
        if len(result) != len(feature_ids):
            raise ValueError("Circular dependency detected during topological sort")

        return result

    def _reverse_topological_sort(self, feature_ids: Set[str]) -> List[str]:
        """Perform reverse topological sort for disable order."""
        # For disabling, we want dependents before dependencies
        # So we reverse the enable order
        enable_order = self._topological_sort(feature_ids)
        return list(reversed(enable_order))

    def get_cache_key(self, operation: str, feature_ids: List[str], **kwargs) -> str:
        """Generate a cache key for dependency resolution results."""
        # Sort feature IDs for consistent cache keys
        sorted_ids = sorted(feature_ids)
        cache_data = {
            "operation": operation,
            "feature_ids": sorted_ids,
            "kwargs": kwargs,
            "graph_hash": self._get_graph_hash(),
        }

        cache_string = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_string.encode()).hexdigest()

    def _get_graph_hash(self) -> str:
        """Get a hash of the current dependency graph state."""
        graph_data = {"nodes": sorted(list(self.graph.nodes)), "edges": []}

        for node in sorted(self.graph.nodes):
            for dep in self.graph.get_dependencies(node):
                graph_data["edges"].append(
                    {
                        "from": node,
                        "to": dep.feature_id,
                        "type": dep.dependency_type.value,
                        "optional": dep.optional,
                    }
                )

        graph_string = json.dumps(graph_data, sort_keys=True)
        return hashlib.md5(graph_string.encode()).hexdigest()

    async def validate_feature_state(self, feature_id: str) -> List[str]:
        """
        Validate that a feature's current state is consistent with its dependencies.

        Returns:
            List of validation warnings/errors
        """
        warnings = []

        if feature_id not in self.features:
            return ["Feature not found"]

        config = self.features[feature_id]
        state = self.states.get(feature_id)

        if not state:
            return ["Feature state not found"]

        # Check if enabled feature has all required dependencies enabled
        if state.enabled:
            for dep in config.dependencies:
                if dep.dependency_type == DependencyType.REQUIRES and not dep.optional:
                    dep_state = self.states.get(dep.feature_id)
                    if not dep_state or not dep_state.enabled:
                        warnings.append(
                            f"Required dependency '{dep.feature_id}' is not enabled"
                        )

        # Check if disabled feature has dependents that are enabled
        if not state.enabled:
            dependents = self.graph.get_dependents(feature_id)
            for dependent in dependents:
                dep_state = self.states.get(dependent)
                if dep_state and dep_state.enabled:
                    warnings.append(
                        f"Dependent feature '{dependent}' is enabled while this feature is disabled"
                    )

        # Check for conflicts
        if state.enabled:
            for dep in config.dependencies:
                if dep.dependency_type == DependencyType.CONFLICTS:
                    dep_state = self.states.get(dep.feature_id)
                    if dep_state and dep_state.enabled:
                        warnings.append(
                            f"Conflicting feature '{dep.feature_id}' is also enabled"
                        )

        return warnings

    async def get_feature_impact(self, feature_id: str) -> Dict[str, Any]:
        """
        Get the impact analysis for enabling/disabling a feature.

        Returns:
            Dictionary with impact analysis
        """
        impact = {
            "feature_id": feature_id,
            "dependencies": [],
            "dependents": [],
            "conflicts": [],
            "impact_score": 0,
        }

        if feature_id not in self.features:
            return impact

        config = self.features[feature_id]

        # Get dependencies
        for dep in config.dependencies:
            dep_state = self.states.get(dep.feature_id)
            impact["dependencies"].append(
                {
                    "feature_id": dep.feature_id,
                    "type": dep.dependency_type.value,
                    "optional": dep.optional,
                    "current_state": dep_state.status.value if dep_state else "unknown",
                    "enabled": dep_state.enabled if dep_state else False,
                }
            )

        # Get dependents
        for dependent in self.graph.get_dependents(feature_id):
            dep_state = self.states.get(dependent)
            impact["dependents"].append(
                {
                    "feature_id": dependent,
                    "current_state": dep_state.status.value if dep_state else "unknown",
                    "enabled": dep_state.enabled if dep_state else False,
                }
            )

        # Get conflicts
        for dep in config.dependencies:
            if dep.dependency_type == DependencyType.CONFLICTS:
                dep_state = self.states.get(dep.feature_id)
                impact["conflicts"].append(
                    {
                        "feature_id": dep.feature_id,
                        "current_state": (
                            dep_state.status.value if dep_state else "unknown"
                        ),
                        "enabled": dep_state.enabled if dep_state else False,
                    }
                )

        # Calculate impact score (simple heuristic)
        impact["impact_score"] = (
            len(impact["dependencies"]) * 1
            + len(impact["dependents"]) * 2
            + len(impact["conflicts"]) * 3
        )

        return impact
