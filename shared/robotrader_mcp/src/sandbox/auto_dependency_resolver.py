"""
Auto Dependency Resolver for Sandbox Execution
Automatically detects and allows missing dependencies during runtime.
"""

import sys
import importlib
import re
from typing import List, Set, Tuple, Optional
from pathlib import Path


class AutoDependencyResolver:
    """
    Automatically resolves and allows missing module dependencies
    during sandbox execution.
    """

    def __init__(self, allowed_modules: Set[str]):
        """
        Initialize with current allowed modules.

        Args:
            allowed_modules: Set of currently allowed module names
        """
        self.allowed_modules = allowed_modules
        self.detected_dependencies: Set[str] = set()
        self.dependency_cache: dict = {}

    def analyze_imports_in_code(self, code: str) -> List[str]:
        """
        Analyze Python code to extract all import statements.

        Args:
            code: Python source code to analyze

        Returns:
            List of imported module names
        """
        imports = []

        # Pattern to match import statements
        patterns = [
            r'import\s+([a-zA-Z_][a-zA-Z0-9_\.]*)',  # import module.submodule
            r'from\s+([a-zA-Z_][a-zA-Z0-9_\.]*)\s+import',  # from module import
        ]

        for pattern in patterns:
            matches = re.findall(pattern, code)
            for match in matches:
                # Extract top-level module name
                module_name = match.split('.')[0]
                if module_name and module_name not in imports:
                    imports.append(module_name)

        return imports

    def detect_missing_dependencies(self, code: str) -> List[str]:
        """
        Detect which imported modules in the code are not allowed.

        Args:
            code: Python source code to analyze

        Returns:
            List of missing module names
        """
        imported_modules = self.analyze_imports_in_code(code)
        missing = []

        for module in imported_modules:
            if module not in self.allowed_modules and module not in self.detected_dependencies:
                missing.append(module)

        return missing

    def resolve_dependencies_recursively(self, modules: List[str]) -> Set[str]:
        """
        Recursively resolve all dependencies for a list of modules.

        Args:
            modules: List of module names to resolve

        Returns:
            Set of all required modules including dependencies
        """
        resolved = set()
        to_process = list(modules)

        while to_process:
            module = to_process.pop(0)
            if module in resolved:
                continue

            try:
                resolved.add(module)
                deps = self.get_module_dependencies(module)
                for dep in deps:
                    if dep not in resolved and dep not in to_process:
                        to_process.append(dep)
            except (ImportError, ModuleNotFoundError):
                # Module not available, skip it
                continue

        return resolved

    def get_module_dependencies(self, module_name: str) -> List[str]:
        """
        Get all internal dependencies for a module.

        Args:
            module_name: Name of the module to analyze

        Returns:
            List of dependency module names
        """
        if module_name in self.dependency_cache:
            return self.dependency_cache[module_name]

        dependencies = set()

        try:
            # Try to import the module
            module = importlib.import_module(module_name)

            # Check for common internal dependencies based on module type
            if module_name in ['statistics']:
                dependencies.update(['_random', 'math', 'numbers'])
            elif module_name in ['datetime']:
                dependencies.update(['_pydatetime', 'time', '_strptime', 'math'])
            elif module_name in ['json']:
                dependencies.update(['_json', 'codecs', 're'])
            elif module_name in ['sqlite3']:
                dependencies.update(['_sqlite3', 'datetime', 'time'])
            elif module_name in ['urllib']:
                dependencies.update(['socket', 'ssl', 'base64', 'hashlib'])
            elif module_name in ['http']:
                dependencies.update(['socket', 'ssl', 'email'])
            elif module_name in ['email']:
                dependencies.update(['socket', 'base64', 'binascii', 'quopri', 'uu'])
            elif module_name in ['xml']:
                dependencies.update(['_elementtree', 're', 'codecs'])
            elif module_name in ['html']:
                dependencies.update(['html.entities', 're'])
            elif module_name in ['encodings']:
                dependencies.update(['codecs', '_codecs'])
            elif module_name in ['pickle']:
                dependencies.update(['_pickle', 'codecs', 'struct', 're'])
            elif module_name in ['decimal']:
                dependencies.update(['_pydecimal', 'numbers', 're'])
            elif module_name in ['fractions']:
                dependencies.update(['numbers', 'math', 'decimal'])
            elif module_name in ['zipfile']:
                dependencies.update(['zlib', 'binascii', 'struct', 'io'])
            elif module_name in ['gzip']:
                dependencies.update(['zlib', 'io', 'struct'])
            elif module_name in ['bz2']:
                dependencies.update(['_bz2', 'io'])
            elif module_name in ['lzma']:
                dependencies.update(['_lzma', 'io'])
            elif module_name in ['ssl']:
                dependencies.update(['_ssl', 'socket', 'hashlib', 'hmac', 'time'])
            elif module_name in ['hashlib']:
                dependencies.update(['_hashlib', '_md5', '_sha1', '_sha256', '_sha512'])
            elif module_name in ['hmac']:
                dependencies.update(['_hashlib', '_operator'])
            elif module_name in ['uuid']:
                dependencies.update(['_uuid', 'time', 'random', 'hashlib', 'os'])
            elif module_name in ['socket']:
                dependencies.update(['socket', 'os', 'io', 'errno'])
            elif module_name in ['threading']:
                dependencies.update(['_thread', 'time', 'traceback', 'warnings'])
            elif module_name in ['multiprocessing']:
                dependencies.update(['_multiprocessing', 'threading', 'queue', 'os'])
            elif module_name in ['concurrent']:
                dependencies.update(['threading', 'queue', 'asyncio'])
            elif module_name in ['asyncio']:
                dependencies.update(['_asyncio', 'selectors', 'socket', 'threading'])
            elif module_name in ['queue']:
                dependencies.update(['threading', 'collections', 'heapq', 'time'])
            elif module_name in ['weakref']:
                dependencies.update(['_weakref', 'collections'])
            elif module_name in ['types']:
                dependencies.update(['typing', 'collections'])
            elif module_name in ['typing']:
                dependencies.update(['types', 'collections'])
            elif module_name in ['inspect']:
                dependencies.update(['importlib', 'linecache', 'os', 'tokenize'])
            elif module_name in ['tokenize']:
                dependencies.update(['token', 'io', 're', 'codecs', 'operator'])
            elif module_name in ['token']:
                dependencies.update(['keyword', 're'])
            elif module_name in ['linecache']:
                dependencies.update(['os', 'tokenize', 'io'])
            elif module_name in ['pkgutil']:
                dependencies.update(['importlib', 'os', 'sys'])
            elif module_name in ['importlib']:
                dependencies.update(['_imp', 'importlib._bootstrap', 'sys', 'types'])
            elif module_name in ['runpy']:
                dependencies.update(['importlib', 'os', 'types', 'io'])
            elif module_name in ['py_compile']:
                dependencies.update(['importlib', 'os', 'sys', 'marshal'])
            elif module_name in ['compileall']:
                dependencies.update(['py_compile', 'os', 'importlib', 'concurrent'])
            elif module_name in ['dis']:
                dependencies.update(['opcode', 'types', 'collections'])
            elif module_name in ['pickletools']:
                dependencies.update(['pickle', 'dis', 'codecs', 're'])
            elif module_name in ['pdb']:
                dependencies.update(['bdb', 'cmd', 'code', 'inspect', 'linecache'])
            elif module_name in ['profile']:
                dependencies.update(['pstats', 'time', 'resource'])
            elif module_name in ['pstats']:
                dependencies.update(['marshal', 'time', 'functools'])
            elif module_name in ['timeit']:
                dependencies.update(['time', 'gc', 'statistics'])
            elif module_name in ['trace']:
                dependencies.update(['linecache', 'os', 'sys', 'threading'])
            elif module_name in ['tracemalloc']:
                dependencies.update(['fnmatch', 'functools', 'linecache', 'os', 'pickle'])
            elif module_name in ['gc']:
                dependencies.update(['types', 'weakref'])
            elif module_name in ['contextvars']:
                dependencies.update(['_contextvars'])
            elif module_name in ['dataclasses']:
                dependencies.update(['typing', 'inspect', 're'])
            elif module_name in ['configparser']:
                dependencies.update(['os', 're', 'collections'])
            elif module_name in ['argparse']:
                dependencies.update(['os', 're', 'copy', 'textwrap'])
            elif module_name in ['gettext']:
                dependencies.update(['os', 're', 'errno'])
            elif module_name in ['locale']:
                dependencies.update(['_locale', 'encodings', 're', 'os'])
            elif module_name in ['calendar']:
                dependencies.update(['datetime', 'locale'])
            elif module_name in ['zoneinfo']:
                dependencies.update(['_zoneinfo', 'json', 'sys'])
            elif module_name in ['sysconfig']:
                dependencies.update(['os', 'json', 'platform'])
            elif module_name in ['platform']:
                dependencies.update(['os', 'sys', 'subprocess', 're'])
            elif module_name in ['subprocess']:
                dependencies.update(['os', 'sys', 'signal', 'time', 'errno'])
            elif module_name in ['tempfile']:
                dependencies.update(['os', 'sys', 'shutil', 'random'])
            elif module_name in ['shutil']:
                dependencies.update(['os', 'sys', 'stat', 'fnmatch', 'collections'])
            elif module_name in ['glob']:
                dependencies.update(['os', 'fnmatch', 're'])
            elif module_name in ['fnmatch']:
                dependencies.update(['re', 'os'])
            elif module_name in ['pathlib']:
                dependencies.update(['os', 'sys', 'io', 're', 'errno'])
            elif module_name in ['urllib']:
                dependencies.update(['socket', 'ssl', 'base64', 'hashlib', 'os'])
            elif module_name in ['email']:
                dependencies.update(['socket', 'base64', 'binascii', 'quopri', 'uu', 're', 'os'])
            elif module_name in ['mailbox']:
                dependencies.update(['os', 'time', 'email', 'calendar'])
            elif module_name in ['mimetypes']:
                dependencies.update(['os', 're', 'email'])
            elif module_name in ['uu']:
                dependencies.update(['os', 'binascii', 're'])
            elif module_name in ['binhex']:
                dependencies.update(['os', 'binascii', 're'])
            elif module_name in ['xdrlib']:
                dependencies.update(['io', 'struct', 'operator'])
            elif module_name in ['plistlib']:
                dependencies.update(['os', 'datetime', 're', 'struct', 'binascii'])
            elif module_name in ['ctypes']:
                dependencies.update(['_ctypes', 'os', 'sys'])
            elif module_name in ['webbrowser']:
                dependencies.update(['os', 'subprocess', 'shlex', 'threading'])

            # Cache the result
            self.dependency_cache[module_name] = list(dependencies)

        except (ImportError, ModuleNotFoundError, AttributeError):
            # Module not available or error during analysis
            pass

        return list(dependencies)

    def suggest_missing_modules(self, code: str) -> List[str]:
        """
        Suggest additional modules that should be allowed for the given code.

        Args:
            code: Python source code to analyze

        Returns:
            List of suggested module names to add to allowed list
        """
        missing = self.detect_missing_dependencies(code)
        if not missing:
            return []

        # Resolve all dependencies for missing modules
        all_deps = self.resolve_dependencies_recursively(missing)

        # Filter out already allowed modules
        suggestions = [dep for dep in all_deps if dep not in self.allowed_modules]

        return sorted(suggestions)

    def generate_patched_allowed_modules(self, code: str) -> Set[str]:
        """
        Generate a new set of allowed modules that includes dependencies for the code.

        Args:
            code: Python source code to analyze

        Returns:
            New set of allowed module names including dependencies
        """
        suggestions = self.suggest_missing_modules(code)
        new_allowed = self.allowed_modules.union(suggestions)
        self.detected_dependencies.update(suggestions)

        return new_allowed


def main():
    """Test the auto dependency resolver."""
    # Test with current allowed modules
    test_allowed = {
        'json', 'math', 'statistics', 'datetime', 'operator', 'itertools',
        'collections', 'random', 'functools', 're', 'string', 'typing',
        'types', 'numbers', 'abc', 'enum', 'copy', 'decimal', 'fractions',
        'hashlib', 'time', 'uuid', 'pathlib', 'inspect', 'textwrap',
        'csv', 'pprint', 'dis', 'traceback', 'warnings', 'heapq', 'bisect',
        'logging', 'sqlite3', 'threading', 'socket', 'urllib', 'http',
        'email', 'xml', 'html', 'ftplib', 'gzip', 'zipfile', 'tarfile',
        'shutil', 'tempfile', 'glob', 'fnmatch', 'subprocess',
        'multiprocessing', 'queue', 'concurrent', 'ssl', 'base64',
        'binascii', 'pickle', 'struct', 'array', 'codecs', 'encodings',
        'unicodedata', 'locale', 'calendar', 'zoneinfo', 'platform',
        'sysconfig', 'importlib', 'imp', 'pkgutil', 'modulefinder',
        'runpy', 'py_compile', 'compileall', 'pdb', 'profile', 'pstats',
        'timeit', 'trace', 'tracemalloc', 'gc', 'weakref', 'atexit',
        'dataclasses', 'argparse', 'configparser', 'xmlrpc', 'socketserver',
        'http.server', 'mailbox', 'mimetypes', 'uu', 'binhex', 'xdrlib',
        'plistlib', 'ctypes', 'webbrowser', 'antigravity', 'this', 'site',
        # Internal modules
        '_io', '_collections', '_collections_abc', '_functools', '_heapq',
        '_thread', '_weakref', '_operator', '_stat', '_sre', '_warnings',
        '_codecs', '_codecs_iso2022', '_ctypes', '_ctypes_test', '_random',
        '_pydatetime', '_abc', '_ast', '_bisect', '_blake2', '_bz2',
        '_csv', '_decimal', '_elementtree', '_hashlib', '_imp', '_json',
        '_locale', '_lsprof', '_lzma', '_md5', '_opcode', '_pickle',
        '_posixsubprocess', '_py_abc', '_pydecimal', '_sha1', '_sha256',
        '_sha3', '_sha512', '_signal', '_socket', '_sqlite3', '_ssl',
        '_string', '_strptime', '_struct', '_tkinter', '_tracemalloc',
        '_weakrefset', 'builtins', 'sysconfig', 'os.path', 'os'
    }

    resolver = AutoDependencyResolver(test_allowed)

    # Test with problematic code
    test_code = '''
import statistics
import datetime
import json
from operator import itemgetter
import tokenize
import linecache
'''

    print("🔍 Analyzing test code for dependencies...")
    suggestions = resolver.suggest_missing_modules(test_code)
    print(f"📝 Suggested additional modules: {suggestions}")

    new_allowed = resolver.generate_patched_allowed_modules(test_code)
    print(f"✅ Total modules after patching: {len(new_allowed)}")


if __name__ == "__main__":
    main()