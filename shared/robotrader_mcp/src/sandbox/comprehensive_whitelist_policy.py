"""
Comprehensive Whitelist Policy for Sandbox
Includes ALL standard library modules to prevent dependency issues.
"""

# Generate a comprehensive list of all standard library modules
# This prevents "Module X is not allowed" errors during execution

COMPREHENSIVE_STDLIB_MODULES = [
    # Core language modules
    "builtins", "sys", "os", "io", "types", "gc", "weakref", "atexit",

    # Data types and structures
    "collections", "itertools", "functools", "operator", "heapq", "bisect",
    "array", "contextvars", "dataclasses", "enum", "typing", "numbers",
    "decimal", "fractions", "random", "statistics", "math",

    # Text processing
    "string", "re", "codecs", "encodings", "unicodedata", "textwrap",
    "difflib", "pprint", "reprlib", "csv", "configparser", "argparse",
    "gettext", "locale", "calendar", "zoneinfo",

    # Binary data
    "base64", "binascii", "quopri", "uu", "struct", "array",

    # File formats
    "json", "pickle", "pickletools", "marshal", "shelve", "dbm",
    "sqlite3", "gzip", "bz2", "lzma", "zipfile", "tarfile", "xdrlib",
    "plistlib", "mailbox", "mimetypes", "email", "email.utils",
    "email.mime", "email.generator", "email.parser", "email.message",
    "xml", "xml.dom", "xml.dom.minidom", "xml.sax", "xml.sax.handler",
    "xml.sax.saxutils", "xml.sax.xmlreader", "xml.etree", "xml.etree.ElementTree",
    "xmlrpc", "xmlrpc.client", "xmlrpc.server", "html", "html.entities",
    "html.parser", "html5lib", "sgmllib", "htmllib", "markupbase",

    # Network and internet
    "socket", "socketserver", "ssl", "urllib", "urllib.parse", "urllib.request",
    "urllib.response", "urllib.error", "http", "http.client", "http.server",
    "http.cookies", "http.cookiejar", "ftplib", "poplib", "imaplib",
    "smtplib", "telnetlib", "uuid", "ipaddress", "email",

    # Concurrency and parallelism
    "threading", "_thread", "queue", "multiprocessing", "multiprocessing.shared_memory",
    "multiprocessing.pool", "multiprocessing.managers", "multiprocessing.dummy",
    "concurrent", "concurrent.futures", "asyncio", "asyncio.streams",
    "asyncio.subprocess", "asyncio.queues", "asyncio.locks", "asyncio.ssl",
    "asyncio.runners", "asyncio.tasks", "asyncio.base_events",
    "asyncio.protocols", "asyncio.transports", "asyncio.events",
    "asyncio.base_subprocess", "asyncio.base_tasks", "asyncio.coroutines",
    "asyncio.base_futures", "asyncio.format_helpers", "asyncio.constants",
    "selectors", "signal", "subprocess", "sched", "time", "timeit",

    # Operating system interface
    "os", "os.path", "pathlib", "tempfile", "shutil", "glob", "fnmatch",
    "linecache", "shlex", "platform", "errno", "stat", "filecmp",
    "fileinput", "sysconfig", "site", "user", "getpass", "getopt",
    "pwd", "spwd", "grp", "crypt", "ctypes", "ctypes.util", "ctypes.wintypes",
    "mmap", "termios", "tty", "pty", "fcntl", "pipes", "posix", "resource",
    "winsound", "winreg", "msvcrt", "_winapi",

    # Development and debugging
    "importlib", "importlib.util", "importlib.machinery", "importlib.abc",
    "imp", "pkgutil", "modulefinder", "inspect", "linecache", "pickle",
    "py_compile", "compileall", "dis", "pickletools", "pdb", "profile",
    "pstats", "timeit", "trace", "tracemalloc", "cProfile", "hotshot",
    "hotshot.stats", "runpy", "parser", "symbol", "token", "tokenize",
    "keyword", "token", "tabnanny", "pyclbr", "pydoc", "pydoc_data",
    "doctest", "unittest", "test", "test.support", "test.support.script_helper",
    "test.support.import_helper", "test.support.threading_helper",
    "test.support.socket_helper", "test.support.os_helper", "test.support.fs_helper",

    # Mathematics and numerics
    "math", "cmath", "statistics", "random", "fractions", "decimal",
    "numbers", "enum", "datetime", "time", "zoneinfo", "calendar",

    # System utilities
    "sys", "os", "io", "pathlib", "shutil", "tempfile", "glob", "fnmatch",
    "linecache", "shlex", "platform", "subprocess", "signal", "resource",
    "errno", "stat", "filecmp", "fileinput", "traceback", "warnings",
    "contextlib", "abc", "copy", "copyreg", "types", "typing",

    # Security and hashing
    "hashlib", "hmac", "secrets", "ssl", "crypt", "uuid", "getpass",

    # Compression
    "zlib", "gzip", "bz2", "lzma", "zipfile", "tarfile",

    # Database
    "sqlite3", "dbm", "dbm.gnu", "dbm.ndbm", "shelve", "bsddb",

    # GUI
    "tkinter", "tkinter.ttk", "tkinter.scrolledtext", "tkinter.dnd2",
    "tkinter.colorchooser", "tkinter.commondialog", "tkinter.filedialog",
    "tkinter.simpledialog", "turtle",

    # Multimedia
    "audioop", "imageop", "aifc", "sunau", "wave", "chunk", "colorsys",
    "rgbimg", "imghdr", "sndhdr", "ossaudiodev", "winsound",

    # Internet protocols
    "urllib", "http", "ftplib", "poplib", "imaplib", "smtplib", "telnetlib",
    "socket", "socketserver", "ssl", "email", "email.mime", "email.generator",
    "email.parser", "email.message", "email.utils", "email.header",
    "email.charset", "email.quoprimime", "email.base64mime", "email.iterators",
    "email.feedparser", "mbox", "mailbox", "mhlib", "mailcap",

    # Web and markup
    "html", "html.parser", "html.entities", "xml", "xml.dom", "xml.dom.minidom",
    "xml.dom.pulldom", "xml.sax", "xml.sax.handler", "xml.sax.saxutils",
    "xml.sax.xmlreader", "xml.etree", "xml.etree.ElementTree", "xmlrpc",
    "xmlrpc.client", "xmlrpc.server", "sgmllib", "htmllib", "markupbase",
    "webbrowser", "antigravity", "this",

    # Development tools
    "py_compile", "compileall", "dis", "pickletools", "pdb", "cProfile",
    "profile", "pstats", "timeit", "trace", "tracemalloc", "gc",
    "weakref", "atexit", "site", "sitecustomize", "usercustomize",

    # Testing
    "unittest", "doctest", "test", "test.support", "test.support.script_helper",
    "test.support.import_helper", "test.support.threading_helper",
    "test.support.socket_helper", "test.support.os_helper", "test.support.fs_helper",

    # Documentation
    "pydoc", "pydoc_data", "help", "apropos",

    # Package management
    "pkgutil", "importlib", "importlib.metadata", "importlib.resources",
    "importlib.abc", "importlib.machinery", "importlib.util", "zipimport",
    "runpy", "imp",

    # System profiling and debugging
    "pstats", "profile", "cProfile", "hotshot", "hotshot.stats",
    "timeit", "trace", "tracemalloc", "gc", "resource", "memoryview",

    # Text encodings (all common ones)
    "encodings.idna", "encodings.punycode", "encodings.unicode_escape",
    "encodings.raw_unicode_escape", "encodings.utf_8", "encodings.utf_16",
    "encodings.utf_32", "encodings.latin_1", "encodings.ascii",
    "encodings.cp1252", "encodings.cp437", "encodings.iso8859_1",
    "encodings.iso8859_15", "encodings.mac_roman", "encodings.big5",
    "encodings.gb2312", "encodings.gbk", "encodings.gb18030",
    "encodings.shift_jis", "encodings.euc_jp", "encodings.koi8_r",
    "encodings.cp866", "encodings.cp850", "encodings.cp852",

    # All internal modules (starting with underscore)
    "_abc", "_aix_support", "_ast", "_asyncio", "_bisect", "_blake2",
    "_bz2", "_codecs", "_codecs_cn", "_codecs_hk", "_codecs_iso2022",
    "_codecs_jp", "_codecs_kr", "_codecs_tw", "_collections", "_collections_abc",
    "_compat_pickle", "_compression", "_contextvars", "_crypt", "_csv",
    "_ctypes", "_ctypes_test", "_curses", "_curses_panel", "_datetime",
    "_decimal", "_elementtree", "_frozen_importlib", "_frozen_importlib_external",
    "_functools", "_gdbm", "_hashlib", "_heapq", "_imp", "_io", "_json",
    "_locale", "_lsprof", "_lzma", "_md5", "_msi", "_multibytecodec",
    "_multiprocessing", "_opcode", "_operator", "_osx_support", "_pickle",
    "_posixsubprocess", "_py_abc", "_pydecimal", "_pylong", "_random",
    "_sha1", "_sha256", "_sha3", "_sha512", "_signal", "_sitebuiltins",
    "_socket", "_sqlite3", "_sre", "_ssl", "_stat", "_string", "_strptime",
    "_struct", "_sysconfigdata", "_sysconfigdata__darwin_darwin",
    "_sysconfigdata__linux_linux", "_testbuffer", "_testcapi",
    "_testimportmultiple", "_testmultiphase", "_thread", "_tkinter",
    "_tracemalloc", "_warnings", "_weakref", "_weakrefset", "_winapi", "_winreg",

    # Additional modules for comprehensive coverage
    "aifc", "anydbm", "argparse", "ast", "asynchat", "asyncore", "atexit",
    "audioop", "base64", "bdb", "binascii", "binhex", "bisect", "builtins",
    "bz2", "cProfile", "calendar", "cgi", "cgitb", "chunk", "cmath",
    "cmd", "code", "codecs", "codeop", "collections", "colorsys",
    "compileall", "concurrent", "configparser", "contextlib", "copy",
    "copyreg", "crypt", "csv", "ctypes", "curses", "datetime", "dbhash",
    "dbm", "decimal", "difflib", "dis", "distutils", "doctest", "dummy_thread",
    "email", "encodings", "enum", "errno", "faulthandler", "fcntl", "filecmp",
    "fileinput", "fnmatch", "formatter", "fractions", "ftplib", "functools",
    "gc", "genericpath", "getopt", "getpass", "gettext", "glob", "grp",
    "gzip", "hashlib", "heapq", "hmac", "html", "html.entities", "html.parser",
    "http", "http.client", "http.cookies", "http.cookiejar", "http.server",
    "imaplib", "imgfile", "imghdr", "imp", "importlib", "inspect", "io",
    "ipaddress", "itertools", "json", "keyword", "linecache", "locale",
    "logging", "lzma", "mailbox", "mailcap", "marshal", "math", "mimetypes",
    "mmap", "modulefinder", "multifile", "multiprocessing", "netrc",
    "nntplib", "ntpath", "numbers", "opcode", "operator", "optparse", "os",
    "ossaudiodev", "parser", "pathlib", "pdb", "pickle", "pickletools",
    "pipes", "pkgutil", "platform", "plistlib", "poplib", "posix", "posixpath",
    "pprint", "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr",
    "pydoc", "queue", "quopri", "random", "re", "readline", "reprlib",
    "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
    "selectors", "shelve", "shlex", "shutil", "signal", "site", "smtpd",
    "smtplib", "sndhdr", "socket", "socketserver", "sqlite3", "sre",
    "sre_compile", "sre_constants", "sre_parse", "ssl", "stat", "statistics",
    "string", "stringprep", "struct", "subprocess", "sunau", "symbol",
    "symtable", "sys", "sysconfig", "syslog", "tabnanny", "tarfile",
    "telnetlib", "tempfile", "termios", "textwrap", "thread", "threading",
    "time", "timeit", "tkinter", "token", "tokenize", "trace", "traceback",
    "tracemalloc", "tty", "turtle", "types", "typing", "unicodedata",
    "unittest", "urllib", "urllib.error", "urllib.parse", "urllib.request",
    "urllib.response", "urllib.robotparser", "uu", "uuid", "venv",
    "warnings", "wave", "weakref", "webbrowser", "winreg", "winsound",
    "wsgiref", "xdrlib", "xml", "xml.dom", "xml.dom.minidom", "xml.dom.pulldom",
    "xml.etree", "xml.etree.ElementTree", "xmlrpc", "xmlrpc.client", "xmlrpc.server",
    "zipapp", "zipfile", "zipimport", "zlib"
]


def create_comprehensive_isolation_policy():
    """
    Create a comprehensive isolation policy that includes all standard library modules.

    Returns:
        IsolationPolicy configured with comprehensive module whitelist
    """
    from .isolation import IsolationPolicy, IsolationLevel

    policy = IsolationPolicy(
        level=IsolationLevel.DEVELOPMENT,
        allowed_imports=COMPREHENSIVE_STDLIB_MODULES,
        max_execution_time_sec=30,
        max_memory_mb=512,
        allow_network=True,
        allowed_domains=["localhost:8000"]
    ).apply_level(IsolationLevel.DEVELOPMENT)

    return policy


def get_comprehensive_module_list():
    """
    Get the comprehensive list of all allowed modules.

    Returns:
        List of module names
    """
    return COMPREHENSIVE_STDLIB_MODULES.copy()


def is_module_allowed(module_name: str) -> bool:
    """
    Check if a module is allowed in the comprehensive policy.

    Args:
        module_name: Name of the module to check

    Returns:
        True if module is allowed, False otherwise
    """
    return module_name in COMPREHENSIVE_STDLIB_MODULES


if __name__ == "__main__":
    print(f"📊 Comprehensive policy includes {len(COMPREHENSIVE_STDLIB_MODULES)} modules")
    print(f"🔍 Internal modules: {len([m for m in COMPREHENSIVE_STDLIB_MODULES if m.startswith('_')])}")
    print(f"📚 Public modules: {len([m for m in COMPREHENSIVE_STDLIB_MODULES if not m.startswith('_')])}")

    # Test some commonly problematic modules
    test_modules = ['statistics', 'datetime', 'tokenize', 'linecache', 'logging', 'io']
    print(f"\n✅ Testing common problematic modules:")
    for module in test_modules:
        status = "✅ ALLOWED" if is_module_allowed(module) else "❌ BLOCKED"
        print(f"   {module}: {status}")