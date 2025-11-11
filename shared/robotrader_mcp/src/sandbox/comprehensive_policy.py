"""
Comprehensive Sandbox Policy Generator
Automatically includes all standard library modules and their dependencies
to prevent dependency chain issues during execution.
"""

import sys
import pkgutil
import importlib
from typing import List, Set


class ComprehensivePolicyGenerator:
    """Generates comprehensive sandbox policies that include all stdlib modules."""

    def __init__(self):
        self.discovered_modules: Set[str] = set()
        self.internal_modules: Set[str] = set()

    def discover_all_stdlib_modules(self) -> List[str]:
        """
        Discover all available standard library modules in the current Python installation.

        Returns:
            List of all standard library module names
        """
        stdlib_modules = set()

        # Core modules that should always be included
        core_modules = {
            'sys', 'os', 'io', 'json', 'math', 'statistics', 'random', 'datetime',
            'collections', 'itertools', 'functools', 'operator', 're', 'string',
            'typing', 'types', 'numbers', 'abc', 'enum', 'copy', 'decimal',
            'fractions', 'hashlib', 'time', 'uuid', 'pathlib', 'inspect',
            'textwrap', 'csv', 'pprint', 'dis', 'traceback', 'warnings',
            'heapq', 'bisect', 'logging', 'sqlite3', 'threading', 'socket',
            'urllib', 'http', 'email', 'xml', 'html', 'ftplib', 'gzip',
            'zipfile', 'tarfile', 'shutil', 'tempfile', 'glob', 'fnmatch',
            'subprocess', 'multiprocessing', 'queue', 'concurrent',
            'ssl', 'hashlib', 'hmac', 'secrets', 'base64', 'binascii',
            'pickle', 'marshal', 'struct', 'array', 'memoryview',
            'codecs', 'encodings', 'unicodedata', 'locale', 'calendar',
            'zoneinfo', 'datetime', 'time', 'platform', 'sysconfig',
            'importlib', 'imp', 'pkgutil', 'modulefinder', 'runpy',
            'py_compile', 'compileall', 'dis', 'pickletools', 'pdb',
            'profile', 'pstats', 'timeit', 'trace', 'tracemalloc',
            'gc', 'weakref', 'atexit', 'queue', 'threading', 'asyncio',
            'contextvars', 'dataclasses', 'enum', 'typing', 'types',
            'inspect', 'gettext', 'argparse', 'configparser', 'csv',
            'json', 'xmlrpc', 'socketserver', 'http.server', 'urllib',
            'email', 'mailbox', 'mimetypes', 'uu', 'binhex', 'xdrlib',
            'plistlib', 'ctypes', 'curses', 'tkinter', 'turtle',
            'webbrowser', 'antigravity', 'this', 'site'
        }

        # Discover modules in the standard library
        for importer, modname, ispkg in pkgutil.iter_modules():
            # Include modules that don't have dots (top-level stdlib modules)
            if '.' not in modname and not modname.startswith('_'):
                try:
                    # Try to import to see if it's a stdlib module
                    module = importlib.import_module(modname)
                    module_file = getattr(module, '__file__', '')
                    if module_file and ('python3.' in module_file or 'Python.framework' in module_file):
                        stdlib_modules.add(modname)
                except (ImportError, ModuleNotFoundError):
                    continue
                except Exception:
                    continue

        # Combine core modules with discovered modules
        all_modules = core_modules.union(stdlib_modules)

        # Sort for consistent output
        return sorted(list(all_modules))

    def discover_internal_modules(self) -> List[str]:
        """
        Discover all internal modules (starting with underscore).

        Returns:
            List of internal module names
        """
        internal_modules = set()

        # Known internal modules that high-level modules depend on
        known_internal = {
            '_io', '_collections', '_collections_abc', '_functools', '_heapq',
            '_thread', '_weakref', '_operator', '_stat', '_sre', '_warnings',
            '_codecs', '_codecs_iso2022', '_ctypes', '_ctypes_test', '_random',
            '_pydatetime', '_abc', '_ast', '_bisect', '_blake2', '_bz2',
            '_csv', '_decimal', '_elementtree', '_hashlib', '_imp',
            '_json', '_locale', '_lsprof', '_lzma', '_md5', '_opcode',
            '_pickle', '_posixsubprocess', '_py_abc', '_pydecimal',
            '_sha1', '_sha256', '_sha3', '_sha512', '_signal',
            '_socket', '_sqlite3', '_ssl', '_string', '_strptime',
            '_struct', '_tkinter', '_tracemalloc', '_weakrefset',
            'builtins', 'sysconfig', 'os.path'
        }

        # Add platform-specific internal modules
        if sys.platform.startswith('darwin'):
            known_internal.update({
                '_osx_support', '_sysconfigdata__darwin_darwin'
            })
        elif sys.platform.startswith('linux'):
            known_internal.update({
                '_sysconfigdata__linux_linux'
            })
        elif sys.platform.startswith('win'):
            known_internal.update({
                '_winapi', '_winreg', '_msi'
            })

        # Discover additional internal modules
        for name in dir(sys.modules):
            if name.startswith('_') and name not in known_internal:
                try:
                    module = sys.modules.get(name)
                    if module and hasattr(module, '__file__'):
                        module_file = module.__file__
                        if module_file and ('python3.' in module_file or 'Python.framework' in module_file):
                            known_internal.add(name)
                except:
                    continue

        return sorted(list(known_internal))

    def generate_comprehensive_policy(self) -> List[str]:
        """
        Generate a comprehensive list of all standard library modules
        and their internal dependencies.

        Returns:
            Comprehensive list of allowed module names
        """
        all_stdlib = self.discover_all_stdlib_modules()
        all_internal = self.discover_internal_modules()

        # Combine and deduplicate
        comprehensive_list = list(set(all_stdlib + all_internal))

        # Sort for consistent output
        return sorted(comprehensive_list)

    def create_isolation_policy_config(self) -> str:
        """
        Generate the Python configuration code for the comprehensive policy.

        Returns:
            String containing the policy configuration
        """
        modules = self.generate_comprehensive_policy()

        # Format as Python list
        module_list = ',\n        '.join([f'"{module}"' for module in modules])

        config = f'''    # Comprehensive standard library modules (auto-generated)
    allowed_imports=[
        {module_list}
    ],
    max_execution_time_sec=30,
    max_memory_mb=512,
    allow_network=True,
    allowed_domains=["localhost:8000"]
).apply_level(IsolationLevel.DEVELOPMENT)'''

        return config


def main():
    """Generate and print the comprehensive policy configuration."""
    generator = ComprehensivePolicyGenerator()

    print("🔍 Discovering comprehensive module list...")
    modules = generator.generate_comprehensive_policy()

    print(f"📊 Found {len(modules)} total modules")
    print(f"   Standard library modules: {len([m for m in modules if not m.startswith('_')])}")
    print(f"   Internal modules: {len([m for m in modules if m.startswith('_')])}")

    print("\n📝 Generated policy configuration:")
    print(generator.create_isolation_policy_config())

    return modules


if __name__ == "__main__":
    main()