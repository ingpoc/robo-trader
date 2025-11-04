"""
Feature Dependency Graph

Graph data structure for managing feature dependencies with cycle detection.
"""

from typing import Dict, List, Set
from collections import defaultdict
from dataclasses import dataclass

from .models import FeatureDependency, DependencyType


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

    def add_feature(self, feature_id: str, dependencies: List[FeatureDependency]) -> None:
        """Add a feature and its dependencies to the graph."""
        self.nodes.add(feature_id)
        self.edges[feature_id] = dependencies

        for dep in dependencies:
            if dep.dependency_type == DependencyType.REQUIRES:
                self.reverse_edges[dep.feature_id].append(feature_id)

    def remove_feature(self, feature_id: str) -> None:
        """Remove a feature from the graph."""
        self.nodes.discard(feature_id)

        if feature_id in self.edges:
            for dep in self.edges[feature_id]:
                if dep.dependency_type == DependencyType.REQUIRES:
                    self.reverse_edges[dep.feature_id].remove(feature_id)
            del self.edges[feature_id]

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
