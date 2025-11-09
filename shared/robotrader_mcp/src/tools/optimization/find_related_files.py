#!/usr/bin/env python3
"""
Find Related Files Tool - Smart File Discovery

Finds files related to a given file or concept using:
- Import analysis (follows import chains)
- Name similarity (coordinators, services, routes)
- Pattern matching (related patterns like State/Repository/Coordinator)
- Recent git changes (files changed together)

Token Savings: Finds exact files instead of blind directory traversal
"""

import os
import ast
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from collections import defaultdict


def find_related_files(
    reference: str,
    relation_type: str = "all",
    max_results: int = 10,
    include_tests: bool = False
) -> Dict[str, Any]:
    """Find files related to a reference file or concept.

    Args:
        reference: File path or concept name (e.g., "BroadcastCoordinator")
        relation_type: Type of relation to find:
            - "imports": Files that import or are imported by reference
            - "similar": Files with similar names/patterns
            - "git_related": Files changed together in git history
            - "all": All of the above

        max_results: Maximum results per category
        include_tests: Include test files in results

    Returns:
        Categorized list of related files with relevance scores

    Token Efficiency:
        Returns focused file list (500-1000 tokens) instead of
        scanning entire directory tree (5k-10k tokens) = 90% reduction
    """

    project_root = Path(os.getcwd())
    results = {
        "reference": reference,
        "relation_type": relation_type,
        "related_files": defaultdict(list),
        "tokens_estimate": 800
    }

    # Determine if reference is a file or concept
    reference_path = project_root / reference
    is_file = reference_path.exists()

    if is_file:
        results["reference_type"] = "file"
        results["reference_path"] = str(reference_path.relative_to(project_root))
    else:
        results["reference_type"] = "concept"
        results["concept_name"] = reference

    # Find import relationships
    if relation_type in ["imports", "all"]:
        if is_file:
            import_related = _find_import_related(reference_path, project_root)
            results["related_files"]["imports"] = import_related[:max_results]

    # Find name/pattern similar files
    if relation_type in ["similar", "all"]:
        similar = _find_similar_files(reference, project_root, include_tests)
        results["related_files"]["similar"] = similar[:max_results]

    # Find git co-change history
    if relation_type in ["git_related", "all"] and is_file:
        git_related = _find_git_related(reference_path, project_root)
        results["related_files"]["git_related"] = git_related[:max_results]

    # Add summary statistics
    total_found = sum(len(files) for files in results["related_files"].values())
    results["summary"] = {
        "total_files_found": total_found,
        "categories": list(results["related_files"].keys()),
        "truncated": total_found > max_results * len(results["related_files"])
    }

    # Add suggestions
    results["suggestions"] = _generate_suggestions(results, is_file)

    return dict(results)


def _find_import_related(file_path: Path, project_root: Path) -> List[Dict[str, Any]]:
    """Find files related by import relationships."""

    related = []

    try:
        with open(file_path, 'r') as f:
            content = f.read()

        if file_path.suffix == '.py':
            # Parse imports
            tree = ast.parse(content)

            imports_from_file = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports_from_file.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports_from_file.add(node.module)

            # Find imported files in project
            for imp in imports_from_file:
                imp_path = _resolve_import_to_file(imp, project_root)
                if imp_path:
                    related.append({
                        "file": str(imp_path.relative_to(project_root)),
                        "relation": "imported_by_reference",
                        "import_name": imp
                    })

            # Find files that import this file
            module_name = _file_to_module_name(file_path, project_root)
            if module_name:
                importing_files = _find_files_importing(module_name, project_root)
                for imp_file in importing_files:
                    related.append({
                        "file": str(imp_file.relative_to(project_root)),
                        "relation": "imports_reference",
                        "module_name": module_name
                    })

    except Exception as e:
        pass  # Silently handle parse errors

    return related


def _find_similar_files(reference: str, project_root: Path, include_tests: bool) -> List[Dict[str, Any]]:
    """Find files with similar names or patterns."""

    similar = []

    # Extract key terms from reference
    if '/' in reference or '\\' in reference:
        # It's a path
        ref_name = Path(reference).stem
    else:
        # It's a concept name
        ref_name = reference

    # Remove common suffixes/prefixes
    clean_name = ref_name
    for suffix in ['Coordinator', 'Service', 'State', 'Repository', 'Manager', 'Handler']:
        if clean_name.endswith(suffix):
            clean_base = clean_name[:-len(suffix)]
            break
    else:
        clean_base = clean_name

    # Search for files with similar patterns
    patterns = [
        f"**/*{clean_base}*.py",
        f"**/*{clean_name}*.py",
        f"**/*{clean_base.lower()}*.py"
    ]

    found_files = set()
    for pattern in patterns:
        for file_path in project_root.glob(pattern):
            if file_path.is_file():
                # Skip tests unless requested
                if not include_tests and 'test' in str(file_path).lower():
                    continue

                # Skip __pycache__
                if '__pycache__' in str(file_path):
                    continue

                rel_path = file_path.relative_to(project_root)
                if rel_path not in found_files:
                    found_files.add(rel_path)

                    # Calculate relevance score
                    score = _calculate_similarity_score(ref_name, file_path.stem)

                    similar.append({
                        "file": str(rel_path),
                        "relation": "name_similarity",
                        "similarity_score": score,
                        "reason": _explain_similarity(ref_name, file_path.stem)
                    })

    # Sort by similarity score
    similar.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)

    return similar


def _find_git_related(file_path: Path, project_root: Path) -> List[Dict[str, Any]]:
    """Find files that were changed together in git history."""

    related = []

    try:
        # Get commits that modified this file
        rel_path = file_path.relative_to(project_root)
        result = subprocess.run(
            ["git", "log", "--format=%H", "--", str(rel_path)],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return related

        commit_hashes = result.stdout.strip().split('\n')[:20]  # Last 20 commits

        # For each commit, find other files changed
        co_changed = defaultdict(int)
        for commit_hash in commit_hashes:
            if not commit_hash:
                continue

            result = subprocess.run(
                ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_hash],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                changed_files = result.stdout.strip().split('\n')
                for changed_file in changed_files:
                    if changed_file and changed_file != str(rel_path):
                        co_changed[changed_file] += 1

        # Sort by frequency
        for file, count in sorted(co_changed.items(), key=lambda x: x[1], reverse=True)[:10]:
            related.append({
                "file": file,
                "relation": "git_co_changed",
                "frequency": count,
                "reason": f"Changed together in {count} commits"
            })

    except Exception as e:
        pass  # Silently handle git errors

    return related


def _resolve_import_to_file(import_name: str, project_root: Path) -> Optional[Path]:
    """Try to resolve an import name to a file path."""

    # Handle project-relative imports
    if import_name.startswith('src.'):
        parts = import_name.split('.')
        potential_path = project_root / '/'.join(parts) / '__init__.py'
        if potential_path.exists():
            return potential_path

        potential_path = project_root / '/'.join(parts[:-1]) / f"{parts[-1]}.py"
        if potential_path.exists():
            return potential_path

    return None


def _file_to_module_name(file_path: Path, project_root: Path) -> Optional[str]:
    """Convert file path to module name."""

    try:
        rel_path = file_path.relative_to(project_root)
        parts = list(rel_path.parts)

        # Remove .py extension
        if parts[-1].endswith('.py'):
            parts[-1] = parts[-1][:-3]

        # Remove __init__
        if parts[-1] == '__init__':
            parts = parts[:-1]

        return '.'.join(parts)
    except:
        return None


def _find_files_importing(module_name: str, project_root: Path) -> List[Path]:
    """Find Python files that import the given module."""

    importing = []

    for py_file in project_root.rglob('*.py'):
        if '__pycache__' in str(py_file):
            continue

        try:
            with open(py_file, 'r') as f:
                content = f.read()

            if f'from {module_name}' in content or f'import {module_name}' in content:
                importing.append(py_file)
        except:
            pass

    return importing


def _calculate_similarity_score(ref_name: str, file_name: str) -> float:
    """Calculate similarity score between two names."""

    ref_lower = ref_name.lower()
    file_lower = file_name.lower()

    # Exact match
    if ref_lower == file_lower:
        return 1.0

    # Contains match
    if ref_lower in file_lower or file_lower in ref_lower:
        return 0.8

    # Word overlap
    ref_words = set(re.findall(r'[A-Z][a-z]+', ref_name))
    file_words = set(re.findall(r'[A-Z][a-z]+', file_name))

    if ref_words and file_words:
        overlap = len(ref_words & file_words) / max(len(ref_words), len(file_words))
        return overlap * 0.6

    return 0.0


def _explain_similarity(ref_name: str, file_name: str) -> str:
    """Explain why two files are similar."""

    ref_lower = ref_name.lower()
    file_lower = file_name.lower()

    if ref_lower == file_lower:
        return "Exact name match"

    if ref_lower in file_lower:
        return f"Contains '{ref_name}'"

    if file_lower in ref_lower:
        return f"Part of '{ref_name}'"

    ref_words = set(re.findall(r'[A-Z][a-z]+', ref_name))
    file_words = set(re.findall(r'[A-Z][a-z]+', file_name))
    common = ref_words & file_words

    if common:
        return f"Shares words: {', '.join(common)}"

    return "Pattern match"


def _generate_suggestions(results: Dict, is_file: bool) -> List[str]:
    """Generate helpful suggestions based on results."""

    suggestions = []

    total_found = results["summary"]["total_files_found"]

    if total_found == 0:
        suggestions.append("No related files found - try different search terms")
        if is_file:
            suggestions.append("File may be standalone or newly created")
    elif total_found > 20:
        suggestions.append(f"Found {total_found} related files - showing top results")
        suggestions.append("Use max_results parameter to see more")

    if "imports" in results["related_files"] and results["related_files"]["imports"]:
        count = len(results["related_files"]["imports"])
        suggestions.append(f"Found {count} files with import relationships")

    if "similar" in results["related_files"] and results["related_files"]["similar"]:
        count = len(results["related_files"]["similar"])
        suggestions.append(f"Found {count} files with similar names/patterns")

    return suggestions


# Schema for MCP integration
def get_schema():
    """Return JSON schema for MCP tool registration."""
    return {
        "name": "find_related_files",
        "description": "Find files related by imports, name similarity, or git history",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reference": {
                    "type": "string",
                    "description": "File path or concept name to find related files for"
                },
                "relation_type": {
                    "type": "string",
                    "enum": ["imports", "similar", "git_related", "all"],
                    "description": "Type of relationship to search for"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results per category (default: 10)"
                },
                "include_tests": {
                    "type": "boolean",
                    "description": "Include test files in results (default: false)"
                }
            },
            "required": ["reference"]
        }
    }


if __name__ == "__main__":
    import sys
    import json

    if len(sys.argv) > 1:
        result = find_related_files(sys.argv[1])
        print(json.dumps(result, indent=2))
