import ast
import json
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

# ============================================================
# APEX AI DEVELOPER
# Step 6 - Production Monitoring
# ============================================================

VERSION = "6.0.0"

PROJECT_ROOT = Path(__file__).resolve().parent
MEMORY_FILE = PROJECT_ROOT / "developer_memory.json"
BACKUP_DIR = PROJECT_ROOT / ".apex_backups"

IGNORED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".idea",
    ".vscode",
}

SAFE_COMMAND_PREFIXES = [
    "python --version",
    "python -m pip --version",
    "pip --version",
    "git status",
    "git branch",
    "git log",
    "git diff --stat",
    "git diff --check",
    "where python",
    "where pip",
    "where code",
    "dir",
    "tree",
]

BLOCKED_COMMANDS = [
    "del",
    "erase",
    "rmdir",
    "rd",
    "format",
    "shutdown",
    "restart-computer",
    "remove-item",
    "rm ",
    "chmod",
    "chown",
    "git push",
    "git reset --hard",
    "git clean",
    "git checkout --",
]

PYTHON_EXTENSIONS = {".py"}

MONITORING_LOG_EXTENSIONS = {
    ".log",
    ".txt",
}

MAX_LOG_READ_SIZE = 1024 * 1024

ERROR_KEYWORDS = [
    "error",
    "exception",
    "traceback",
    "critical",
    "fatal",
    "failed",
    "failure",
]

WARNING_KEYWORDS = [
    "warning",
    "warn",
]


# ============================================================
# MEMORY
# ============================================================


def create_default_memory():
    return {
        "version": VERSION,
        "created_at": datetime.now().isoformat(),
        "scans": [],
        "syntax_errors": [],
        "import_checks": [],
        "fixes": [],
        "backups": [],
        "terminal_commands": [],
        "release_checks": [],
        "release_preparations": [],
        "monitoring_history": [],
        "monitoring_alerts": [],
    }


def load_memory():
    if not MEMORY_FILE.exists():
        return create_default_memory()

    try:
        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            memory = json.load(file)

        memory.setdefault(
            "version",
            VERSION,
        )
        memory.setdefault(
            "scans",
            [],
        )
        memory.setdefault(
            "syntax_errors",
            [],
        )
        memory.setdefault(
            "import_checks",
            [],
        )
        memory.setdefault(
            "fixes",
            [],
        )
        memory.setdefault(
            "backups",
            [],
        )
        memory.setdefault(
            "terminal_commands",
            [],
        )
        memory.setdefault(
            "release_checks",
            [],
        )
        memory.setdefault(
            "release_preparations",
            [],
        )
        memory.setdefault(
            "monitoring_history",
            [],
        )
        memory.setdefault("monitoring_alerts", [])

        return memory

    except (
        json.JSONDecodeError,
        OSError,
    ):
        return create_default_memory()


def save_memory(memory):
    with open(
        MEMORY_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            memory,
            file,
            indent=4,
            ensure_ascii=False,
        )


MEMORY = load_memory()


# ============================================================
# PROJECT SCAN
# ============================================================


def is_ignored(path):
    return any(part in IGNORED_PARTS for part in path.parts)


def scan_project():
    files = []
    folders = set()

    for root, dirnames, filenames in os.walk(PROJECT_ROOT):
        root_path = Path(root)

        dirnames[:] = [name for name in dirnames if name not in IGNORED_PARTS]

        if is_ignored(root_path):
            continue

        for dirname in dirnames:
            folder_path = root_path / dirname

            if not is_ignored(folder_path):
                folders.add(folder_path)

        for filename in filenames:
            file_path = root_path / filename

            if not is_ignored(file_path):
                files.append(file_path)

    return files, folders


# ============================================================
# PYTHON SYNTAX CHECK
# ============================================================


def check_python_syntax(files):
    errors = []
    checked = 0

    for file_path in files:
        if file_path.suffix.lower() not in PYTHON_EXTENSIONS:
            continue

        checked += 1

        try:
            source = file_path.read_text(encoding="utf-8-sig")

            compile(
                source,
                str(file_path),
                "exec",
            )

        except SyntaxError as error:
            errors.append(
                {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "line": error.lineno,
                    "column": error.offset,
                    "message": error.msg,
                }
            )

        except UnicodeDecodeError as error:
            errors.append(
                {
                    "file": str(file_path.relative_to(PROJECT_ROOT)),
                    "line": None,
                    "column": None,
                    "message": (f"Unicode decode error: {error}"),
                }
            )

    MEMORY["syntax_errors"] = errors
    save_memory(MEMORY)

    return checked, errors


# ============================================================
# IMPORT ANALYSIS
# ============================================================


def check_python_imports(files):
    results = []
    errors = []

    for file_path in files:
        if file_path.suffix.lower() not in PYTHON_EXTENSIONS:
            continue

        try:
            source = file_path.read_text(encoding="utf-8-sig")

            tree = ast.parse(
                source,
                filename=str(file_path),
            )

            imports = []

            for node in ast.walk(tree):

                if isinstance(node, ast.Import):
                    for item in node.names:
                        imports.append(item.name)

                elif isinstance(
                    node,
                    ast.ImportFrom,
                ):
                    module = node.module or ""
                    imports.append(module)

            relative_name = str(file_path.relative_to(PROJECT_ROOT))

            results.append(
                {
                    "file": relative_name,
                    "imports": imports,
                    "count": len(imports),
                }
            )

            print(f"📦 {file_path.name}: " f"{len(imports)} imports")

        except Exception as error:
            relative_name = str(file_path.relative_to(PROJECT_ROOT))

            errors.append(
                {
                    "file": relative_name,
                    "message": str(error),
                }
            )

    MEMORY["import_checks"] = results
    save_memory(MEMORY)

    return results, errors


# ============================================================
# HEALTH CHECK
# ============================================================


def health_check():
    try:
        python_version = platform.python_version()
        operating_system = platform.system()
        machine = platform.machine()

        return {
            "status": "healthy",
            "python": python_version,
            "os": operating_system,
            "machine": machine,
        }

    except Exception as error:
        return {
            "status": "unhealthy",
            "error": str(error),
        }


# ============================================================
# SAFE AUTO-FIX
# ============================================================


def safe_auto_fix(files, syntax_errors):
    fixes = []

    if not syntax_errors:
        print("✅ No syntax errors require fixing.")
        return fixes

    error_files = {item["file"] for item in syntax_errors if item.get("file")}

    for file_path in files:
        relative_name = str(file_path.relative_to(PROJECT_ROOT))

        if relative_name not in error_files:
            continue

        if file_path.suffix.lower() != ".py":
            continue

        try:
            original = file_path.read_text(encoding="utf-8-sig")

            fixed = original

            fixed = fixed.replace(
                "\r\n",
                "\n",
            )

            fixed = "\n".join(line.rstrip() for line in fixed.split("\n"))

            fixed = fixed.rstrip("\n") + "\n"

            if fixed != original:
                file_path.write_text(
                    fixed,
                    encoding="utf-8",
                )

                fixes.append(
                    {
                        "file": relative_name,
                        "type": "safe_format_cleanup",
                    }
                )

        except Exception as error:
            fixes.append(
                {
                    "file": relative_name,
                    "type": "fix_failed",
                    "error": str(error),
                }
            )

    MEMORY["fixes"].extend(fixes)
    save_memory(MEMORY)

    return fixes


# ============================================================
# BACKUP
# ============================================================


def create_backup():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    backup_path = BACKUP_DIR / f"backup_{timestamp}"

    try:
        BACKUP_DIR.mkdir(exist_ok=True)

        shutil.copytree(
            PROJECT_ROOT,
            backup_path,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(
                ".git",
                ".venv",
                "venv",
                "__pycache__",
                ".apex_backups",
            ),
        )

        record = {
            "path": str(backup_path),
            "type": "pre_release_backup",
        }

        MEMORY["backups"].append(
            {
                "timestamp": datetime.now().isoformat(),
                **record,
            }
        )

        save_memory(MEMORY)

        print(f"💾 Backup created: " f"{backup_path}")

        return backup_path

    except Exception as error:
        print(f"❌ Backup failed: {error}")

        return None


# ============================================================
# TERMINAL
# ============================================================


def command_is_blocked(command):
    normalized = command.strip().lower()

    for blocked in BLOCKED_COMMANDS:

        if normalized == blocked.strip() or normalized.startswith(blocked):
            return True

    return False


def command_is_safe(command):
    normalized = command.strip().lower()

    if command_is_blocked(normalized):
        return False

    return any(
        normalized == prefix or normalized.startswith(prefix + " ")
        for prefix in SAFE_COMMAND_PREFIXES
    )


def run_terminal_command(
    command,
    allow_unsafe=False,
    timeout=30,
):
    print("\n🖥️ APEX Terminal")
    print(f"Command: {command}")

    if command_is_blocked(command):
        print("⛔ Command is blocked " "by APEX safety policy.")

        return {
            "success": False,
            "blocked": True,
            "output": "",
            "error": "Blocked command",
        }

    if not command_is_safe(command) and not allow_unsafe:
        print("🛡️ Command requires approval.")

        return {
            "success": False,
            "blocked": False,
            "requires_approval": True,
            "output": "",
            "error": ("Command requires approval"),
        }

    try:
        result = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = (result.stdout or "").strip()

        error = (result.stderr or "").strip()

        print("✅ Command completed.")

        if output:
            print("📤 OUTPUT:")
            print(output)

        if error:
            print("📥 ERROR:")
            print(error)

        record = {
            "command": command,
            "return_code": result.returncode,
            "success": result.returncode == 0,
            "output": output[-10000:],
            "error": error[-10000:],
        }

        MEMORY["terminal_commands"].append(
            {
                "timestamp": datetime.now().isoformat(),
                **record,
            }
        )

        save_memory(MEMORY)

        return record

    except subprocess.TimeoutExpired:
        print("⏱️ Command timed out.")

        record = {
            "command": command,
            "success": False,
            "error": "Command timed out",
        }

        MEMORY["terminal_commands"].append(
            {
                "timestamp": datetime.now().isoformat(),
                **record,
            }
        )

        save_memory(MEMORY)

        return record

    except Exception as error:
        print(f"❌ Terminal error: {error}")

        record = {
            "command": command,
            "success": False,
            "error": str(error),
        }

        MEMORY["terminal_commands"].append(
            {
                "timestamp": datetime.now().isoformat(),
                **record,
            }
        )

        save_memory(MEMORY)

        return record


# ============================================================
# VS CODE
# ============================================================


def detect_vscode():
    result = run_terminal_command("where code")

    if result.get("success") and result.get("output"):
        return True

    return False


# ============================================================
# GIT RELEASE CHECK
# ============================================================


def release_git_check():
    print("\n🚦 APEX Release Safety Check")

    status = run_terminal_command("git status")

    branch = run_terminal_command("git branch")

    log = run_terminal_command("git log")

    checks = {
        "git_status": bool(status.get("success")),
        "git_branch": bool(branch.get("success")),
        "git_log": bool(log.get("success")),
        "clean_worktree": False,
        "has_remote_push": False,
    }

    if status.get("success"):
        output = status.get(
            "output",
            "",
        ).lower()

        clean_markers = [
            "nothing to commit, working tree clean",
            "working tree clean",
        ]

        checks["clean_worktree"] = any(marker in output for marker in clean_markers)

    MEMORY["release_checks"].append(
        {
            "timestamp": datetime.now().isoformat(),
            **checks,
        }
    )

    save_memory(MEMORY)

    return checks


# ============================================================
# RELEASE MANIFEST
# ============================================================


def create_release_manifest(
    files,
    health,
    syntax_errors,
    import_errors,
):
    python_files = [
        str(path.relative_to(PROJECT_ROOT))
        for path in files
        if path.suffix.lower() == ".py"
    ]

    manifest = {
        "developer_version": VERSION,
        "created_at": datetime.now().isoformat(),
        "project": PROJECT_ROOT.name,
        "python_files": python_files,
        "python_file_count": len(python_files),
        "syntax_errors": len(syntax_errors),
        "import_analysis_errors": len(import_errors),
        "health": health,
        "release_policy": {
            "automatic_push": False,
            "automatic_production_change": False,
            "automatic_delete": False,
            "automatic_package_update": False,
        },
    }

    manifest_file = PROJECT_ROOT / "apex_release_manifest.json"

    try:
        with open(
            manifest_file,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                manifest,
                file,
                indent=4,
                ensure_ascii=False,
            )

        print("📄 Release manifest created: " f"{manifest_file.name}")

        return manifest_file

    except OSError as error:
        print("❌ Could not create " f"release manifest: {error}")

        return None


# ============================================================
# RELEASE PREPARATION
# ============================================================


def prepare_release(
    files,
    health,
    syntax_errors,
    import_errors,
):
    print("\n📦 Preparing safe release package...")

    if syntax_errors:
        print("⛔ Release preparation stopped: " "Python syntax errors exist.")

        return {
            "prepared": False,
            "reason": "syntax_errors",
        }

    if import_errors:
        print("⛔ Release preparation stopped: " "import analysis errors exist.")

        return {
            "prepared": False,
            "reason": "import_analysis_errors",
        }

    if health.get("status") != "healthy":
        print("⛔ Release preparation stopped: " "health check failed.")

        return {
            "prepared": False,
            "reason": "health_check_failed",
        }

    backup_path = create_backup()

    if backup_path is None:
        print("⛔ Release preparation stopped: " "backup failed.")

        return {
            "prepared": False,
            "reason": "backup_failed",
        }

    manifest_file = create_release_manifest(
        files,
        health,
        syntax_errors,
        import_errors,
    )

    if manifest_file is None:
        return {
            "prepared": False,
            "reason": "manifest_failed",
        }

    result = {
        "prepared": True,
        "backup": str(backup_path),
        "manifest": str(manifest_file),
        "push_required": False,
        "production_change": False,
    }

    MEMORY["release_preparations"].append(
        {
            "timestamp": datetime.now().isoformat(),
            **result,
        }
    )

    save_memory(MEMORY)

    print("✅ Safe release preparation completed.")

    print("🛡️ No Git push was performed.")

    print("🛡️ No production change was performed.")

    return result


# ============================================================
# MONITORING - MEMORY / SYSTEM
# ============================================================


def get_system_memory():
    """
    Reads Windows physical memory information
    without requiring an additional package.
    """

    if platform.system() != "Windows":
        return {
            "available": False,
            "reason": "Windows-specific monitor",
        }

    try:
        import ctypes

        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                (
                    "dwLength",
                    ctypes.c_ulong,
                ),
                (
                    "dwMemoryLoad",
                    ctypes.c_ulong,
                ),
                (
                    "ullTotalPhys",
                    ctypes.c_ulonglong,
                ),
                (
                    "ullAvailPhys",
                    ctypes.c_ulonglong,
                ),
                (
                    "ullTotalPageFile",
                    ctypes.c_ulonglong,
                ),
                (
                    "ullAvailPageFile",
                    ctypes.c_ulonglong,
                ),
                (
                    "ullTotalVirtual",
                    ctypes.c_ulonglong,
                ),
                (
                    "ullAvailVirtual",
                    ctypes.c_ulonglong,
                ),
                (
                    "ullAvailExtendedVirtual",
                    ctypes.c_ulonglong,
                ),
            ]

        status = MEMORYSTATUSEX()
        status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)

        success = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))

        if not success:
            return {
                "available": False,
                "reason": ("GlobalMemoryStatusEx failed"),
            }

        total_gb = status.ullTotalPhys / (1024**3)

        available_gb = status.ullAvailPhys / (1024**3)

        used_gb = total_gb - available_gb

        return {
            "available": True,
            "load_percent": int(status.dwMemoryLoad),
            "total_gb": round(
                total_gb,
                2,
            ),
            "available_gb": round(
                available_gb,
                2,
            ),
            "used_gb": round(
                used_gb,
                2,
            ),
        }

    except Exception as error:
        return {
            "available": False,
            "reason": str(error),
        }


# ============================================================
# MONITORING - DISK
# ============================================================


def get_disk_health():
    try:
        usage = shutil.disk_usage(PROJECT_ROOT)

        total_gb = usage.total / (1024**3)

        free_gb = usage.free / (1024**3)

        used_gb = total_gb - free_gb

        used_percent = (used_gb / total_gb) * 100 if total_gb > 0 else 0

        return {
            "available": True,
            "total_gb": round(
                total_gb,
                2,
            ),
            "used_gb": round(
                used_gb,
                2,
            ),
            "free_gb": round(
                free_gb,
                2,
            ),
            "used_percent": round(
                used_percent,
                2,
            ),
        }

    except Exception as error:
        return {
            "available": False,
            "reason": str(error),
        }


# ============================================================
# MONITORING - LOG FILES
# ============================================================


def find_log_files(files):
    log_files = []

    for file_path in files:
        if file_path.suffix.lower() in MONITORING_LOG_EXTENSIONS:
            log_files.append(file_path)

    return log_files


def analyze_log_file(file_path):
    result = {
        "file": str(file_path.relative_to(PROJECT_ROOT)),
        "errors": 0,
        "warnings": 0,
        "critical": 0,
        "matches": [],
    }

    try:
        if file_path.stat().st_size > MAX_LOG_READ_SIZE:
            with open(
                file_path,
                "rb",
            ) as file:
                file.seek(
                    -MAX_LOG_READ_SIZE,
                    os.SEEK_END,
                )

                content = file.read().decode(
                    "utf-8",
                    errors="replace",
                )
        else:
            content = file_path.read_text(
                encoding="utf-8",
                errors="replace",
            )

        for line_number, line in enumerate(
            content.splitlines(),
            start=1,
        ):
            normalized = line.lower()

            if any(keyword in normalized for keyword in ERROR_KEYWORDS):
                result["errors"] += 1

                if "critical" in normalized or "fatal" in normalized:
                    result["critical"] += 1

                if len(result["matches"]) < 20:
                    result["matches"].append(
                        {
                            "line": line_number,
                            "type": "error",
                            "text": line[:500],
                        }
                    )

            elif any(keyword in normalized for keyword in WARNING_KEYWORDS):
                result["warnings"] += 1

                if len(result["matches"]) < 20:
                    result["matches"].append(
                        {
                            "line": line_number,
                            "type": "warning",
                            "text": line[:500],
                        }
                    )

        return result

    except Exception as error:
        result["read_error"] = str(error)
        return result


# ============================================================
# MONITORING ALERTS
# ============================================================


def build_monitoring_alerts(
    memory_health,
    disk_health,
    log_results,
):
    alerts = []

    if memory_health.get("available"):
        memory_load = memory_health.get(
            "load_percent",
            0,
        )

        if memory_load >= 90:
            alerts.append(
                {
                    "level": "critical",
                    "type": "memory",
                    "message": ("Physical memory usage " "is very high."),
                    "value": memory_load,
                }
            )

        elif memory_load >= 80:
            alerts.append(
                {
                    "level": "warning",
                    "type": "memory",
                    "message": ("Physical memory usage " "is high."),
                    "value": memory_load,
                }
            )

    if disk_health.get("available"):
        disk_load = disk_health.get(
            "used_percent",
            0,
        )

        if disk_load >= 95:
            alerts.append(
                {
                    "level": "critical",
                    "type": "disk",
                    "message": ("Disk usage is critically high."),
                    "value": disk_load,
                }
            )

        elif disk_load >= 90:
            alerts.append(
                {
                    "level": "warning",
                    "type": "disk",
                    "message": ("Disk usage is high."),
                    "value": disk_load,
                }
            )

    for result in log_results:
        critical_count = result.get(
            "critical",
            0,
        )

        error_count = result.get(
            "errors",
            0,
        )

        warning_count = result.get(
            "warnings",
            0,
        )

        if critical_count > 0:
            alerts.append(
                {
                    "level": "critical",
                    "type": "log",
                    "file": result["file"],
                    "message": ("Critical entries detected " "in application log."),
                    "value": critical_count,
                }
            )

        elif error_count > 0:
            alerts.append(
                {
                    "level": "error",
                    "type": "log",
                    "file": result["file"],
                    "message": ("Error entries detected " "in application log."),
                    "value": error_count,
                }
            )

        elif warning_count > 0:
            alerts.append(
                {
                    "level": "warning",
                    "type": "log",
                    "file": result["file"],
                    "message": ("Warning entries detected " "in application log."),
                    "value": warning_count,
                }
            )

    return alerts


# ============================================================
# PRODUCTION MONITORING
# ============================================================


def run_production_monitoring(
    files,
    health,
):
    print("\n📡 APEX Production Monitoring...")

    start_time = time.time()

    memory_health = get_system_memory()

    disk_health = get_disk_health()

    log_files = find_log_files(files)

    log_results = []

    for log_file in log_files:
        result = analyze_log_file(log_file)

        log_results.append(result)

    alerts = build_monitoring_alerts(
        memory_health,
        disk_health,
        log_results,
    )

    duration = round(
        time.time() - start_time,
        3,
    )

    monitoring_status = "healthy"

    if any(alert["level"] == "critical" for alert in alerts):
        monitoring_status = "critical"

    elif any(alert["level"] == "error" for alert in alerts):
        monitoring_status = "error"

    elif any(alert["level"] == "warning" for alert in alerts):
        monitoring_status = "warning"

    result = {
        "timestamp": datetime.now().isoformat(),
        "developer_version": VERSION,
        "duration_seconds": duration,
        "status": monitoring_status,
        "application_health": health,
        "memory": memory_health,
        "disk": disk_health,
        "log_files_checked": len(log_files),
        "logs": log_results,
        "alerts": alerts,
        "automatic_action": False,
    }

    MEMORY["monitoring_history"].append(result)

    MEMORY["monitoring_alerts"].extend(alerts)

    MEMORY["monitoring_history"] = MEMORY["monitoring_history"][-100:]

    MEMORY["monitoring_alerts"] = MEMORY["monitoring_alerts"][-200:]

    save_memory(MEMORY)

    print(f"❤️ Monitoring status: " f"{monitoring_status}")

    if memory_health.get("available"):
        print("🧠 Memory usage: " f"{memory_health['load_percent']}%")

    if disk_health.get("available"):
        print("💽 Disk usage: " f"{disk_health['used_percent']}%")

    print(f"📝 Log files checked: " f"{len(log_files)}")

    print(f"🚨 Alerts detected: " f"{len(alerts)}")

    if alerts:
        for alert in alerts:
            print(f"   [{alert['level'].upper()}] " f"{alert['message']}")

    else:
        print("✅ No monitoring alerts detected.")

    print("🛡️ Automatic production action: " "DISABLED")

    return result


# ============================================================
# MAIN
# ============================================================


def main():
    print("=" * 50)
    print("🤖 APEX AI DEVELOPER")
    print("📌 Step 6 - Production Monitoring")
    print("=" * 50)

    print(f"📁 Project: {PROJECT_ROOT}")

    print(f"🧠 Version: {VERSION}")

    print("\n🚀 Starting APEX Developer Step 6...")

    # --------------------------------------------------------
    # Project Scan
    # --------------------------------------------------------

    print("\n🔍 Scanning APEX project...")

    files, folders = scan_project()

    print(f"✅ Files found: {len(files)}")

    print(f"📂 Folders found: {len(folders)}")

    MEMORY["scans"].append(
        {
            "timestamp": datetime.now().isoformat(),
            "files": len(files),
            "folders": len(folders),
            "version": VERSION,
        }
    )

    save_memory(MEMORY)

    # --------------------------------------------------------
    # Syntax
    # --------------------------------------------------------

    print("\n🐍 Checking Python syntax...")

    checked, syntax_errors = check_python_syntax(files)

    print(f"📊 Python files checked: " f"{checked}")

    if syntax_errors:
        print(f"❌ Python syntax errors: " f"{len(syntax_errors)}")

        for error in syntax_errors:
            print(
                f"   {error['file']} - " f"line {error['line']}: " f"{error['message']}"
            )

    else:
        print("✅ No Python syntax errors found.")

    # --------------------------------------------------------
    # Imports
    # --------------------------------------------------------

    print("\n📦 Checking Python imports...")

    import_results, import_errors = check_python_imports(files)

    if import_errors:
        print(f"❌ Import analysis errors: " f"{len(import_errors)}")

    else:
        print("✅ Import analysis completed.")

    # --------------------------------------------------------
    # Health
    # --------------------------------------------------------

    print("\n❤️ APEX Health Check...")

    health = health_check()

    print(f"Status: {health.get('status')}")

    print(f"Python: {health.get('python')}")

    print(f"OS: {health.get('os')}")

    print(f"Machine: {health.get('machine')}")

    # --------------------------------------------------------
    # Safe Auto-Fix
    # --------------------------------------------------------

    print("\n🛠️ APEX Safe Auto-Fix...")

    fixes = safe_auto_fix(
        files,
        syntax_errors,
    )

    if fixes:
        print(f"🛠️ Safe fixes applied: " f"{len(fixes)}")

    else:
        print("✅ No syntax errors require fixing.")

    # --------------------------------------------------------
    # Terminal Diagnostics
    # --------------------------------------------------------

    print("\n🔧 Running terminal diagnostics...")

    diagnostics = []

    diagnostics.append(run_terminal_command("python --version"))

    diagnostics.append(run_terminal_command("where python"))

    diagnostics.append(run_terminal_command("pip --version"))

    diagnostics.append(run_terminal_command("git status"))

    # --------------------------------------------------------
    # VS Code
    # --------------------------------------------------------

    print("\n🧩 Checking VS Code...")

    vscode_detected = detect_vscode()

    if vscode_detected:
        print("🧩 VS Code detected.")

    else:
        print("ℹ️ VS Code command was not detected.")

    # --------------------------------------------------------
    # Release Safety
    # --------------------------------------------------------

    release_checks = release_git_check()

    print("\n📋 Release safety:")

    print(
        "🌿 Git status check:",
        "OK" if release_checks["git_status"] else "FAILED",
    )

    print(
        "🌿 Git branch check:",
        "OK" if release_checks["git_branch"] else "FAILED",
    )

    print(
        "🌿 Git log check:",
        "OK" if release_checks["git_log"] else "FAILED",
    )

    print(
        "🧹 Working tree:",
        "CLEAN" if release_checks["clean_worktree"] else "HAS CHANGES",
    )

    # --------------------------------------------------------
    # Release Preparation
    # --------------------------------------------------------

    release_result = prepare_release(
        files,
        health,
        syntax_errors,
        import_errors,
    )

    # --------------------------------------------------------
    # Step 6 Monitoring
    # --------------------------------------------------------

    monitoring_result = run_production_monitoring(
        files,
        health,
    )

    # --------------------------------------------------------
    # Final Report
    # --------------------------------------------------------

    final_health = health_check()

    print("\n" + "=" * 50)

    print("📋 STEP 6 REPORT")

    print("=" * 50)

    print(f"📁 Files: {len(files)}")

    print(f"📂 Folders: {len(folders)}")

    print(f"🐍 Initial syntax errors: " f"{len(syntax_errors)}")

    print(f"📦 Import errors: " f"{len(import_errors)}")

    print(f"🛠️ Safe fixes applied: " f"{len(fixes)}")

    print(f"🖥️ Terminal diagnostics: " f"{len(diagnostics)}")

    print(f"🧩 VS Code detected: " f"{vscode_detected}")

    print(f"💾 Release backup: " f"{release_result.get('prepared', False)}")

    print(f"📡 Monitoring status: " f"{monitoring_result.get('status')}")

    print(f"🚨 Monitoring alerts: " f"{len(monitoring_result.get('alerts', []))}")

    print(f"❤️ Final health: " f"{final_health.get('status')}")

    print("🛡️ Automatic production action: DISABLED")

    if (
        final_health.get("status") == "healthy"
        and not syntax_errors
        and not import_errors
        and release_result.get("prepared")
    ):
        print("\n✅ STEP 6 COMPLETED SUCCESSFULLY.")

    else:
        print("\n⚠️ STEP 6 COMPLETED " "WITH CHECKS REQUIRED.")

    print("=" * 50)


if __name__ == "__main__":
    main()
