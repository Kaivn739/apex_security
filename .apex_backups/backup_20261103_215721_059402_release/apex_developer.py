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
# Stable Foundation - Steps 1 to 9
#
# STEP 9:
# Controlled Change Engine
#
# IMPORTANT:
# Step 9 creates a controlled change plan.
# It does NOT automatically modify source code.
# It does NOT perform Git push.
# It does NOT perform production deployment.
# ============================================================

VERSION = "9.0.0"

PROJECT_ROOT = Path(__file__).resolve().parent

MEMORY_FILE = PROJECT_ROOT / "developer_memory.json"
BACKUP_DIR = PROJECT_ROOT / ".apex_backups"
REMEDIATION_LOG_DIR = PROJECT_ROOT / ".apex_remediation_logs"
MANIFEST_FILE = PROJECT_ROOT / "apex_release_manifest.json"
CHANGE_PLAN_FILE = PROJECT_ROOT / "apex_change_plan.json"

PYTHON_EXTENSIONS = {".py"}

MONITORING_LOG_EXTENSIONS = {
    ".log",
    ".txt",
}

MAX_LOG_READ_SIZE = 1024 * 1024

MAX_MEMORY_ITEMS = 500
MAX_TERMINAL_OUTPUT = 10000

IGNORED_PARTS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".idea",
    ".vscode",
    ".apex_backups",
    ".apex_remediation_logs",
}

SAFE_COMMAND_PREFIXES = (
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
)

BLOCKED_COMMANDS = (
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
)

ERROR_KEYWORDS = (
    "error",
    "exception",
    "traceback",
    "critical",
    "fatal",
    "failed",
    "failure",
)

WARNING_KEYWORDS = (
    "warning",
    "warn",
)


# ============================================================
# GENERAL HELPERS
# ============================================================


def now_iso():
    return datetime.now().isoformat()


def relative_path(path):
    try:
        return str(Path(path).resolve().relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def trim_text(
    value,
    limit=MAX_TERMINAL_OUTPUT,
):
    if value is None:
        return ""

    value = str(value)

    if len(value) <= limit:
        return value

    return value[-limit:]


def remember(
    key,
    value,
):
    MEMORY.setdefault(
        key,
        [],
    )

    MEMORY[key].append(value)

    if len(MEMORY[key]) > MAX_MEMORY_ITEMS:
        MEMORY[key] = MEMORY[key][-MAX_MEMORY_ITEMS:]


# ============================================================
# MEMORY MANAGEMENT
# ============================================================


def create_default_memory():
    return {
        "schema_version": 3,
        "developer_version": VERSION,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "scans": [],
        "syntax_errors": [],
        "import_checks": [],
        "import_runtime_checks": [],
        "fixes": [],
        "backups": [],
        "terminal_commands": [],
        "release_checks": [],
        "release_preparations": [],
        "monitoring_history": [],
        "monitoring_alerts": [],
        "remediations": [],
        "deployments": [],
        "pipeline_runs": [],
        "change_plans": [],
        "change_applications": [],
    }


def normalize_memory(memory):
    default = create_default_memory()

    for key, value in default.items():
        memory.setdefault(
            key,
            value,
        )

    memory["schema_version"] = 3
    memory["developer_version"] = VERSION
    memory["updated_at"] = now_iso()

    return memory


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

        if not isinstance(memory, dict):
            return create_default_memory()

        return normalize_memory(memory)

    except (
        json.JSONDecodeError,
        OSError,
        TypeError,
    ):

        print("⚠️ Existing memory could not be loaded.")

        print("⚠️ Creating a fresh developer memory.")

        return create_default_memory()


def save_memory(memory):
    """
    Atomic memory write.

    The main memory file is replaced only after the
    temporary JSON file has been successfully written.
    """

    memory = normalize_memory(memory)

    temp_file = MEMORY_FILE.with_suffix(".tmp")

    try:

        with open(
            temp_file,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                memory,
                file,
                indent=4,
                ensure_ascii=False,
            )

            file.flush()
            os.fsync(file.fileno())

        os.replace(
            temp_file,
            MEMORY_FILE,
        )

    except Exception:

        try:

            if temp_file.exists():
                temp_file.unlink()

        except OSError:
            pass

        raise


MEMORY = load_memory()


# ============================================================
# PROJECT SCAN
# ============================================================


def is_ignored(path):
    path = Path(path)

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

    files.sort()
    folders = sorted(folders)

    return files, folders


# ============================================================
# PYTHON SYNTAX CHECK
# ============================================================


def check_python_syntax(files):
    errors = []
    checked = 0

    for file_path in files:

        if file_path.suffix.lower() != ".py":
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
                    "file": relative_path(file_path),
                    "line": error.lineno,
                    "column": error.offset,
                    "message": error.msg,
                }
            )

        except UnicodeDecodeError as error:

            errors.append(
                {
                    "file": relative_path(file_path),
                    "line": None,
                    "column": None,
                    "message": ("Unicode decode error: " f"{error}"),
                }
            )

        except OSError as error:

            errors.append(
                {
                    "file": relative_path(file_path),
                    "line": None,
                    "column": None,
                    "message": ("File read error: " f"{error}"),
                }
            )

    MEMORY["syntax_errors"] = errors

    save_memory(MEMORY)

    return checked, errors


# ============================================================
# AST IMPORT ANALYSIS
# ============================================================


def check_python_imports(files):
    results = []
    errors = []

    for file_path in files:

        if file_path.suffix.lower() != ".py":
            continue

        try:

            source = file_path.read_text(encoding="utf-8-sig")

            tree = ast.parse(
                source,
                filename=str(file_path),
            )

            imports = []

            for node in ast.walk(tree):

                if isinstance(
                    node,
                    ast.Import,
                ):

                    for item in node.names:

                        imports.append(
                            {
                                "type": "import",
                                "module": item.name,
                            }
                        )

                elif isinstance(
                    node,
                    ast.ImportFrom,
                ):

                    imports.append(
                        {
                            "type": "from",
                            "module": (node.module or ""),
                            "level": node.level,
                        }
                    )

            result = {
                "file": relative_path(file_path),
                "imports": imports,
                "count": len(imports),
            }

            results.append(result)

            print(f"📦 {file_path.name}: " f"{len(imports)} imports")

        except Exception as error:

            errors.append(
                {
                    "file": relative_path(file_path),
                    "message": str(error),
                }
            )

    MEMORY["import_checks"] = results

    save_memory(MEMORY)

    return results, errors


# ============================================================
# RUNTIME IMPORT CHECK
#
# IMPORTANT:
# Project files are NOT executed here.
# ============================================================


def check_runtime_imports(files):
    results = []
    errors = []

    python_files = [path for path in files if path.suffix.lower() == ".py"]

    for file_path in python_files:

        result = {
            "file": relative_path(file_path),
            "status": "not_executed",
            "message": (
                "Runtime execution skipped "
                "for safety. AST import analysis "
                "completed."
            ),
        }

        results.append(result)

    MEMORY["import_runtime_checks"] = results

    save_memory(MEMORY)

    return results, errors


# ============================================================
# HEALTH CHECK
# ============================================================


def health_check():
    try:

        return {
            "status": "healthy",
            "python": platform.python_version(),
            "os": platform.system(),
            "machine": platform.machine(),
            "project_exists": PROJECT_ROOT.exists(),
            "memory_file": MEMORY_FILE.exists(),
        }

    except Exception as error:

        return {
            "status": "unhealthy",
            "error": str(error),
        }


# ============================================================
# SAFE AUTO-FIX
# ============================================================


def safe_auto_fix(
    files,
    syntax_errors,
):
    """
    STEP 5 — Safe Auto-Fix

    Performs conservative formatting cleanup only.

    Safety rules:
    - Processes only Python files listed in syntax_errors.
    - Never overwrites a file unless the candidate passes
      Python syntax validation.
    - Creates a backup before modifying a file.
    - Preserves the original UTF-8 BOM when present.
    - Restores the original bytes if writing or validation fails.
    - Returns only successfully applied fixes.
    - Records skipped and failed operations in memory.
    - Never claims to repair arbitrary Python syntax errors.
    """

    fixes = []
    memory_records = []

    # --------------------------------------------------------
    # STEP 5.1 — Validate input
    # --------------------------------------------------------

    if not isinstance(syntax_errors, (list, tuple)):
        print(
            "⚠️ Safe Auto-Fix skipped: "
            "syntax_errors must be a list or tuple."
        )
        return fixes

    if not syntax_errors:
        print(
            "✅ No syntax errors require fixing."
        )
        return fixes

    if not isinstance(files, (list, tuple)):
        print(
            "⚠️ Safe Auto-Fix skipped: "
            "files must be a list or tuple."
        )
        return fixes

    error_files = {
        item.get("file")
        for item in syntax_errors
        if isinstance(item, dict)
        and item.get("file")
    }

    if not error_files:
        print(
            "⚠️ No identifiable Python files "
            "were found in the syntax error report."
        )
        return fixes

    # --------------------------------------------------------
    # STEP 5.2 — Process only identified Python files
    # --------------------------------------------------------

    for file_path in files:

        try:
            if not isinstance(file_path, Path):
                file_path = Path(file_path)

            if file_path.suffix.lower() != ".py":
                continue

            relative_name = relative_path(
                file_path
            )

            if relative_name not in error_files:
                continue

            if not file_path.is_file():
                memory_records.append(
                    {
                        "file": relative_name,
                        "type": "fix_skipped_missing_file",
                        "timestamp": now_iso(),
                    }
                )

                print(
                    f"⚠️ Skipped missing file: "
                    f"{relative_name}"
                )
                continue

            # ------------------------------------------------
            # STEP 5.3 — Read and preserve original bytes
            # ------------------------------------------------

            original_bytes = file_path.read_bytes()

            has_utf8_bom = original_bytes.startswith(
                b"\xef\xbb\xbf"
            )

            try:
                original = original_bytes.decode(
                    "utf-8-sig"
                )

            except UnicodeDecodeError as error:

                memory_records.append(
                    {
                        "file": relative_name,
                        "type": "fix_skipped_encoding_error",
                        "error": str(error),
                        "timestamp": now_iso(),
                    }
                )

                print(
                    f"⚠️ Skipped encoding error: "
                    f"{relative_name}"
                )
                continue

            # ------------------------------------------------
            # STEP 5.4 — Conservative formatting cleanup
            # ------------------------------------------------

            fixed = original.replace(
                "\r\n",
                "\n",
            )

            fixed = "\n".join(
                line.rstrip()
                for line in fixed.split("\n")
            )

            fixed = fixed.rstrip("\n") + "\n"

            # No changes are necessary.
            if fixed == original:
                memory_records.append(
                    {
                        "file": relative_name,
                        "type": "fix_skipped_no_changes",
                        "timestamp": now_iso(),
                    }
                )
                continue

            # ------------------------------------------------
            # STEP 5.5 — Validate candidate before writing
            # ------------------------------------------------

            try:
                compile(
                    fixed,
                    str(file_path),
                    "exec",
                )

            except (SyntaxError, ValueError, TypeError) as error:

                memory_records.append(
                    {
                        "file": relative_name,
                        "type": (
                            "fix_skipped_syntax_invalid"
                        ),
                        "error": str(error),
                        "timestamp": now_iso(),
                    }
                )

                print(
                    f"⚠️ Candidate remains invalid; "
                    f"original preserved: {relative_name}"
                )
                continue

            # ------------------------------------------------
            # STEP 5.6 — Create a unique backup
            # ------------------------------------------------

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S_%f"
            )

            safe_name = (
                relative_name
                .replace("\\", "_")
                .replace("/", "_")
                .replace(":", "_")
            )

            backup_path = (
                BACKUP_DIR
                / (
                    f"{safe_name}."
                    f"step5_{timestamp}.bak"
                )
            )

            try:
                BACKUP_DIR.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                shutil.copy2(
                    file_path,
                    backup_path,
                )

                # Confirm the backup is byte-for-byte identical.
                if backup_path.read_bytes() != original_bytes:
                    raise OSError(
                        "Backup verification failed."
                    )

            except Exception as error:

                memory_records.append(
                    {
                        "file": relative_name,
                        "type": "fix_skipped_backup_error",
                        "error": str(error),
                        "timestamp": now_iso(),
                    }
                )

                print(
                    f"⚠️ Backup failed; original preserved: "
                    f"{relative_name}"
                )
                continue

            # ------------------------------------------------
            # STEP 5.7 — Prepare output bytes
            # ------------------------------------------------

            try:
                fixed_bytes = fixed.encode(
                    "utf-8"
                )

                if has_utf8_bom:
                    fixed_bytes = (
                        b"\xef\xbb\xbf"
                        + fixed_bytes
                    )

                # Confirm candidate bytes decode correctly.
                candidate_text = fixed_bytes.decode(
                    "utf-8-sig"
                )

                # Validate the exact text that will be written.
                compile(
                    candidate_text,
                    str(file_path),
                    "exec",
                )

            except Exception as error:

                memory_records.append(
                    {
                        "file": relative_name,
                        "type": "fix_skipped_validation_error",
                        "error": str(error),
                        "timestamp": now_iso(),
                    }
                )

                print(
                    f"⚠️ Candidate validation failed: "
                    f"{relative_name}"
                )
                continue

            # ------------------------------------------------
            # STEP 5.8 — Write and verify the candidate
            # ------------------------------------------------

            try:
                file_path.write_bytes(
                    fixed_bytes
                )

                written_bytes = file_path.read_bytes()

                if written_bytes != fixed_bytes:
                    raise OSError(
                        "Written bytes do not match candidate."
                    )

                written_text = written_bytes.decode(
                    "utf-8-sig"
                )

                compile(
                    written_text,
                    str(file_path),
                    "exec",
                )

            except Exception as error:

                # Attempt to restore the exact original bytes.
                try:
                    file_path.write_bytes(
                        original_bytes
                    )

                    if file_path.read_bytes() != original_bytes:
                        raise OSError(
                            "Original restoration verification failed."
                        )

                    restore_status = "restored"

                except Exception as restore_error:
                    restore_status = (
                        "restore_failed: "
                        + str(restore_error)
                    )

                memory_records.append(
                    {
                        "file": relative_name,
                        "type": "fix_failed",
                        "error": str(error),
                        "restore_status": restore_status,
                        "backup": str(backup_path),
                        "timestamp": now_iso(),
                    }
                )

                print(
                    f"❌ Fix failed: {relative_name}"
                )

                if restore_status == "restored":
                    print(
                        "↩️ Original file restored."
                    )
                else:
                    print(
                        "🚨 Restoration failed. "
                        "Use the verified backup:"
                    )
                    print(
                        str(backup_path)
                    )

                continue

            # ------------------------------------------------
            # STEP 5.9 — Record successful fix
            # ------------------------------------------------

            fix_record = {
                "file": relative_name,
                "type": "safe_format_cleanup",
                "backup": str(backup_path),
                "timestamp": now_iso(),
            }

            fixes.append(
                fix_record
            )

            memory_records.append(
                fix_record.copy()
            )

            print(
                f"✅ Safe formatting cleanup applied: "
                f"{relative_name}"
            )

        except Exception as error:

            # Keep processing other files if one file fails.
            try:
                failed_name = relative_path(
                    file_path
                )
            except Exception:
                failed_name = str(file_path)

            memory_records.append(
                {
                    "file": failed_name,
                    "type": "fix_failed",
                    "error": str(error),
                    "timestamp": now_iso(),
                }
            )

            print(
                f"⚠️ Safe Auto-Fix could not process: "
                f"{failed_name}"
            )

    # --------------------------------------------------------
    # STEP 5.10 — Persist memory records
    # --------------------------------------------------------

    if memory_records:

        try:
            if not isinstance(
                MEMORY.get("fixes"),
                list,
            ):
                MEMORY["fixes"] = []

            MEMORY["fixes"].extend(
                memory_records
            )

            save_memory(
                MEMORY
            )

        except Exception as error:
            print(
                "⚠️ Fix records could not be saved "
                f"to memory: {error}"
            )

    # --------------------------------------------------------
    # STEP 5.11 — Return successful fixes only
    # --------------------------------------------------------

    print(
        "📊 STEP 5 summary:"
    )

    print(
        f"   Successful fixes: {len(fixes)}"
    )

    print(
        f"   Recorded operations: "
        f"{len(memory_records)}"
    )

    return fixes
def revalidate_after_fixes(files):
    print("\n🔎 Re-validating project " "after safe fixes...")

    checked, syntax_errors = check_python_syntax(files)

    print(f"🐍 Python files re-checked: " f"{checked}")
        
    if syntax_errors:

        print("❌ Syntax errors after fixes: " f"{len(syntax_errors)}")

        for error in syntax_errors[:20]:

            print(
                f"   ❌ {error.get('file')} "
                f"line {error.get('line')}: "
                f"{error.get('message')}"
            )

    else:

        print("✅ Re-validation passed. " "No Python syntax errors.")

    import_results, import_errors = check_python_imports(files)

    (
        runtime_import_results,
        runtime_import_errors,
    ) = check_runtime_imports(files)

    combined_import_errors = import_errors + runtime_import_errors

    print("📦 Import analysis errors " "after fixes: " f"{len(combined_import_errors)}")

    return (
        checked,
        syntax_errors,
        import_results,
        combined_import_errors,
    )


# ============================================================
# BACKUP
# ============================================================


def create_backup(reason="manual"):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    backup_path = BACKUP_DIR / f"backup_{timestamp}_{reason}"

    try:

        BACKUP_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )

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
                ".apex_remediation_logs",
            ),
        )

        record = {
            "timestamp": now_iso(),
            "path": str(backup_path),
            "reason": reason,
            "developer_version": VERSION,
        }

        remember(
            "backups",
            record,
        )

        save_memory(MEMORY)

        print(f"💾 Backup created: " f"{backup_path}")

        return backup_path

    except Exception as error:

        print(f"❌ Backup failed: {error}")

        return None


# ============================================================
# COMMAND SECURITY
# ============================================================


def command_is_blocked(command):
    normalized = command.strip().lower()

    return any(
        normalized == blocked.strip() or normalized.startswith(blocked)
        for blocked in BLOCKED_COMMANDS
    )


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

        print("⛔ Command blocked by " "APEX safety policy.")

        return {
            "success": False,
            "blocked": True,
            "requires_approval": False,
            "output": "",
            "error": "Blocked command",
        }

    if not command_is_safe(command) and not allow_unsafe:

        print("🛡️ Command requires " "explicit approval.")

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

        output = trim_text(result.stdout)

        error = trim_text(result.stderr)

        record = {
            "timestamp": now_iso(),
            "command": command,
            "return_code": (result.returncode),
            "success": (result.returncode == 0),
            "output": output,
            "error": error,
        }

        remember(
            "terminal_commands",
            record,
        )

        save_memory(MEMORY)

        if result.returncode == 0:

            print("✅ Command completed.")

        else:

            print("⚠️ Command returned code " f"{result.returncode}.")

        if output:

            print("📤 OUTPUT:")
            print(output)

        if error:

            print("📥 ERROR:")
            print(error)

        return record

    except subprocess.TimeoutExpired:

        record = {
            "timestamp": now_iso(),
            "command": command,
            "success": False,
            "error": "Command timed out",
        }

        remember(
            "terminal_commands",
            record,
        )

        save_memory(MEMORY)

        print("⏱️ Command timed out.")

        return record

    except Exception as error:

        record = {
            "timestamp": now_iso(),
            "command": command,
            "success": False,
            "error": str(error),
        }

        remember(
            "terminal_commands",
            record,
        )

        save_memory(MEMORY)

        print(f"❌ Terminal error: {error}")

        return record


# ============================================================
# VS CODE
# ============================================================


def detect_vscode():
    result = run_terminal_command("where code")

    return bool(result.get("success") and result.get("output"))


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
        "automatic_push": False,
    }

    if status.get("success"):

        output = status.get(
            "output",
            "",
        ).lower()

        checks["clean_worktree"] = (
            "working tree clean" in output or "nothing to commit" in output
        )

    record = {
        "timestamp": now_iso(),
        **checks,
    }

    remember(
        "release_checks",
        record,
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
        relative_path(path) for path in files if path.suffix.lower() == ".py"
    ]

    manifest = {
        "schema_version": 2,
        "developer_version": VERSION,
        "created_at": now_iso(),
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
            "automatic_destructive_action": False,
        },
        "future_step_policy": {
            "requires_validation": True,
            "requires_backup": True,
            "requires_explicit_gate": True,
        },
    }

    try:

        temp_file = MANIFEST_FILE.with_suffix(".tmp")

        with open(
            temp_file,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                manifest,
                file,
                indent=4,
                ensure_ascii=False,
            )

            file.flush()

            os.fsync(file.fileno())

        os.replace(
            temp_file,
            MANIFEST_FILE,
        )

        print("📄 Release manifest created: " f"{MANIFEST_FILE.name}")

        return MANIFEST_FILE

    except OSError as error:

        print("❌ Could not create manifest: " f"{error}")

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
    print("\n📦 Preparing safe release...")

    if syntax_errors:

        return {
            "prepared": False,
            "reason": "syntax_errors",
        }

    if import_errors:

        return {
            "prepared": False,
            "reason": ("import_analysis_errors"),
        }

    if health.get("status") != "healthy":

        return {
            "prepared": False,
            "reason": ("health_check_failed"),
        }

    backup_path = create_backup(reason="release")

    if backup_path is None:

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

    remember(
        "release_preparations",
        {
            "timestamp": now_iso(),
            **result,
        },
    )

    save_memory(MEMORY)

    print("✅ Safe release preparation " "completed.")

    print("🛡️ Git push: NOT performed.")

    print("🛡️ Production change: " "NOT performed.")

    return result


# ============================================================
# SYSTEM MEMORY MONITORING
# ============================================================


def get_system_memory():
    if platform.system() != "Windows":

        return {
            "available": False,
            "reason": ("Windows-specific monitor"),
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
                "reason": ("GlobalMemoryStatusEx " "failed"),
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
# DISK MONITORING
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
# LOG MONITORING
# ============================================================


def find_log_files(files):
    return [path for path in files if path.suffix.lower() in MONITORING_LOG_EXTENSIONS]


def analyze_log_file(file_path):
    result = {
        "file": relative_path(file_path),
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

        for (
            line_number,
            line,
        ) in enumerate(
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

        load = memory_health.get(
            "load_percent",
            0,
        )

        if load >= 90:

            alerts.append(
                {
                    "level": "critical",
                    "type": "memory",
                    "message": ("Physical memory " "usage is very high."),
                    "value": load,
                }
            )

        elif load >= 80:

            alerts.append(
                {
                    "level": "warning",
                    "type": "memory",
                    "message": ("Physical memory " "usage is high."),
                    "value": load,
                }
            )

    if disk_health.get("available"):

        load = disk_health.get(
            "used_percent",
            0,
        )

        if load >= 95:

            alerts.append(
                {
                    "level": "critical",
                    "type": "disk",
                    "message": ("Disk usage is " "critically high."),
                    "value": load,
                }
            )

        elif load >= 90:

            alerts.append(
                {
                    "level": "warning",
                    "type": "disk",
                    "message": ("Disk usage is high."),
                    "value": load,
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
                    "message": ("Critical log entries " "detected."),
                    "value": critical_count,
                }
            )

        elif error_count > 0:

            alerts.append(
                {
                    "level": "error",
                    "type": "log",
                    "file": result["file"],
                    "message": ("Error log entries " "detected."),
                    "value": error_count,
                }
            )

        elif warning_count > 0:

            alerts.append(
                {
                    "level": "warning",
                    "type": "log",
                    "file": result["file"],
                    "message": ("Warning log entries " "detected."),
                    "value": warning_count,
                }
            )

    return alerts


# ============================================================
# STEP 6 - PRODUCTION MONITORING
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

    log_results = [analyze_log_file(path) for path in log_files]

    alerts = build_monitoring_alerts(
        memory_health,
        disk_health,
        log_results,
    )

    duration = round(
        time.time() - start_time,
        3,
    )

    status = "healthy"

    levels = {alert["level"] for alert in alerts}

    if "critical" in levels:

        status = "critical"

    elif "error" in levels:

        status = "error"

    elif "warning" in levels:

        status = "warning"

    result = {
        "timestamp": now_iso(),
        "developer_version": VERSION,
        "duration_seconds": duration,
        "status": status,
        "application_health": health,
        "memory": memory_health,
        "disk": disk_health,
        "log_files_checked": len(log_files),
        "logs": log_results,
        "alerts": alerts,
        "automatic_action": False,
    }

    remember(
        "monitoring_history",
        result,
    )

    MEMORY["monitoring_alerts"].extend(alerts)

    MEMORY["monitoring_alerts"] = MEMORY["monitoring_alerts"][-200:]

    save_memory(MEMORY)

    print(f"❤️ Monitoring status: " f"{status}")

    if memory_health.get("available"):

        print("🧠 Memory usage: " f"{memory_health['load_percent']}%")

    if disk_health.get("available"):

        print("💽 Disk usage: " f"{disk_health['used_percent']}%")

    print("📝 Log files checked: " f"{len(log_files)}")

    print("🚨 Alerts detected: " f"{len(alerts)}")

    return result


# ============================================================
# STEP 7 - SAFE SELF-HEALING
# ============================================================


def remediate_disk_space():
    """
    Only removes generated Python cache files.

    No user files, source files, databases,
    logs, or Git files are deleted.
    """

    cleaned_bytes = 0
    removed_items = 0

    try:

        for root, dirs, _ in os.walk(PROJECT_ROOT):

            if "__pycache__" not in dirs:
                continue

            cache_path = Path(root) / "__pycache__"

            for item in cache_path.iterdir():

                try:

                    if item.is_file():

                        cleaned_bytes += item.stat().st_size

                        item.unlink()

                        removed_items += 1

                except Exception:
                    pass

        return {
            "type": ("python_cache_cleanup"),
            "status": "success",
            "cleaned_bytes": (cleaned_bytes),
            "removed_items": (removed_items),
            "message": ("Python cache cleanup " "completed."),
        }

    except Exception as error:

        return {
            "type": ("python_cache_cleanup"),
            "status": "failed",
            "error": str(error),
        }


def auto_remediate_alerts(
    monitoring_result,
):
    print("\n🩹 APEX Self-Healing Engine...")

    remediation_actions = []

    alerts = monitoring_result.get(
        "alerts",
        [],
    )

    if not alerts:

        print("✅ No alerts requiring " "remediation.")

        return remediation_actions

    for alert in alerts:

        alert_type = alert.get("type")

        level = alert.get("level")

        if alert_type == "disk" and level in {
            "warning",
            "critical",
        }:

            action = remediate_disk_space()

            remediation_actions.append(action)

        elif alert_type == "memory" and level in {
            "warning",
            "critical",
        }:

            remediation_actions.append(
                {
                    "type": "memory_alert",
                    "status": "observed",
                    "message": (
                        "Memory pressure "
                        "detected. No unsafe "
                        "automatic action "
                        "was performed."
                    ),
                }
            )

        elif alert_type == "log":

            remediation_actions.append(
                {
                    "type": "log_alert",
                    "status": "observed",
                    "file": alert.get("file"),
                    "message": (
                        "Log alert recorded. " "Automatic log reset " "is disabled."
                    ),
                }
            )

    record = {
        "timestamp": now_iso(),
        "actions_count": len(remediation_actions),
        "details": remediation_actions,
    }

    remember(
        "remediations",
        record,
    )

    save_memory(MEMORY)

    print(
        "✅ Self-Healing analysis " "completed: " f"{len(remediation_actions)} actions."
    )

    return remediation_actions


# ============================================================
# STEP 8 - ORCHESTRATION
# ============================================================


def run_autonomous_orchestrator(
    files,
    health,
    syntax_errors,
    import_errors,
    monitoring_result,
    remediation_result,
    release_result,
):
    print("\n" + "=" * 60)

    print("🚀 APEX STEP 8")

    print("Autonomous Orchestration Gate")

    print("=" * 60)

    ready_for_release = (
        health.get("status") == "healthy"
        and len(syntax_errors) == 0
        and len(import_errors) == 0
        and release_result.get(
            "prepared",
            False,
        )
    )

    monitoring_safe = monitoring_result.get("status") not in {
        "critical",
        "error",
    }

    release_ready = ready_for_release and monitoring_safe

    result = {
        "timestamp": now_iso(),
        "developer_version": VERSION,
        "ready_for_release": (release_ready),
        "syntax_errors": len(syntax_errors),
        "import_errors": len(import_errors),
        "remediations_observed": len(remediation_result),
        "monitoring_status": (monitoring_result.get("status")),
        "release_prepared": (
            release_result.get(
                "prepared",
                False,
            )
        ),
        "deployment_performed": False,
        "production_changed": False,
        "git_push_performed": False,
    }

    if release_ready:

        result["status"] = "READY_FOR_DEPLOYMENT"

        print("\n✅ All safety gates passed.")

        print("🛡️ System is READY for a " "future deployment stage.")

        print("🛑 Actual deployment was " "NOT performed.")

    else:

        result["status"] = "DEPLOYMENT_BLOCKED"

        print("\n⛔ Deployment gate blocked.")

    remember(
        "deployments",
        result,
    )

    save_memory(MEMORY)

    return result


# ============================================================
# PIPELINE STATE
# ============================================================


def build_pipeline_state(
    files,
    folders,
    syntax_errors,
    import_errors,
    health,
    monitoring_result,
    remediation_result,
    deployment_result,
):
    return {
        "developer_version": VERSION,
        "timestamp": now_iso(),
        "project": {
            "root": str(PROJECT_ROOT),
            "files": len(files),
            "folders": len(folders),
        },
        "validation": {
            "syntax_errors": len(syntax_errors),
            "import_analysis_errors": len(import_errors),
            "health": health.get("status"),
        },
        "monitoring": {
            "status": (monitoring_result.get("status")),
            "alerts": len(
                monitoring_result.get(
                    "alerts",
                    [],
                )
            ),
        },
        "remediation": {
            "actions": len(remediation_result),
        },
        "deployment_gate": {
            "status": (deployment_result.get("status")),
            "performed": (
                deployment_result.get(
                    "deployment_performed",
                    False,
                )
            ),
        },
        "next_stage_ready": (deployment_result.get("status") == "READY_FOR_DEPLOYMENT"),
    }


# ============================================================
# STEP 9 - CONTROLLED CHANGE ENGINE
#
# This stage creates a validated change plan.
#
# It DOES NOT:
# - edit source files automatically
# - delete source files
# - push to Git
# - deploy to production
#
# Future controlled changes must pass:
# backup -> approval -> change -> validation -> rollback if failed
# ============================================================


def build_change_plan(
    files,
    health,
    syntax_errors,
    import_errors,
    monitoring_result,
    deployment_result,
):
    python_files = [
        relative_path(path) for path in files if path.suffix.lower() == ".py"
    ]

    gates = {
        "health": (health.get("status") == "healthy"),
        "syntax_clean": (len(syntax_errors) == 0),
        "imports_clean": (len(import_errors) == 0),
        "monitoring_safe": (
            monitoring_result.get("status")
            not in {
                "critical",
                "error",
            }
        ),
        "deployment_gate_ready": (
            deployment_result.get("status") == "READY_FOR_DEPLOYMENT"
        ),
    }

    plan_status = "READY_FOR_APPROVAL" if all(gates.values()) else "BLOCKED"

    plan = {
        "schema_version": 1,
        "developer_version": VERSION,
        "created_at": now_iso(),
        "stage": ("STEP_9_CONTROLLED_CHANGE_ENGINE"),
        "status": plan_status,
        "project": PROJECT_ROOT.name,
        "python_files": python_files,
        "gates": gates,
        "requested_changes": [],
        "policy": {
            "automatic_source_edit": False,
            "automatic_delete": False,
            "automatic_git_push": False,
            "automatic_production_change": False,
            "requires_explicit_approval": True,
            "requires_backup_before_change": True,
            "requires_post_change_validation": True,
            "rollback_required_on_failed_validation": True,
        },
        "message": (
            "Step 9 creates a controlled "
            "change plan. No source code "
            "is modified by this stage."
        ),
    }

    try:

        temp_file = CHANGE_PLAN_FILE.with_suffix(".tmp")

        with open(
            temp_file,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                plan,
                file,
                indent=4,
                ensure_ascii=False,
            )

            file.flush()

            os.fsync(file.fileno())

        os.replace(
            temp_file,
            CHANGE_PLAN_FILE,
        )

    except OSError as error:

        plan["status"] = "BLOCKED"

        plan["write_error"] = str(error)

    remember(
        "change_plans",
        plan,
    )

    save_memory(MEMORY)

    print("\n" + "=" * 60)

    print("🧠 STEP 9 - CONTROLLED " "CHANGE ENGINE")

    print("=" * 60)

    print("📋 Change plan: " f"{plan['status']}")

    print("🛡️ Automatic source edit: False")

    print("🛡️ Automatic Git push: False")

    print("🛡️ Automatic production " "change: False")

    print("🔐 Explicit approval required: " "True")

    print("📄 Plan file: " f"{CHANGE_PLAN_FILE.name}")

    return plan


# ============================================================
# FINAL PIPELINE STATE
# ============================================================


def build_final_pipeline_state(
    pipeline_state,
    release_result,
    change_plan,
):
    pipeline_state["release_prepared"] = release_result.get(
        "prepared",
        False,
    )

    pipeline_state["step_9"] = {
        "status": change_plan.get("status"),
        "plan_file": str(CHANGE_PLAN_FILE),
        "source_modified": False,
        "approval_required": True,
    }

    pipeline_state["next_stage_ready"] = (
        change_plan.get("status") == "READY_FOR_APPROVAL"
    )

    return pipeline_state


# ============================================================
# MAIN PIPELINE
# ============================================================


def main():
    pipeline_start = time.time()

    print("=" * 60)

    print("🤖 APEX AI DEVELOPER")

    print("📌 Stable Foundation - " "Steps 1 to 9")

    print(f"🧠 Version: {VERSION}")

    print("=" * 60)

    print(f"📁 Project: {PROJECT_ROOT}")

    # --------------------------------------------------------
    # STEP 1
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print("STEP 1 - PROJECT SCAN")

    print("=" * 60)

    files, folders = scan_project()

    print(f"✅ Files: {len(files)}")

    print(f"📂 Folders: {len(folders)}")

    remember(
        "scans",
        {
            "timestamp": now_iso(),
            "files": len(files),
            "folders": len(folders),
            "version": VERSION,
        },
    )

    save_memory(MEMORY)

    # --------------------------------------------------------
    # STEP 2
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print("STEP 2 - PYTHON VALIDATION")

    print("=" * 60)

    checked, syntax_errors = check_python_syntax(files)

    print(f"🐍 Python files checked: " f"{checked}")

    if syntax_errors:

        print(f"❌ Syntax errors: " f"{len(syntax_errors)}")

    else:

        print("✅ No Python syntax errors.")

    # --------------------------------------------------------
    # STEP 3
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print("STEP 3 - IMPORT ANALYSIS")

    print("=" * 60)

    (
        import_results,
        import_errors,
    ) = check_python_imports(files)

    (
        runtime_import_results,
        runtime_import_errors,
    ) = check_runtime_imports(files)

    combined_import_errors = import_errors + runtime_import_errors

    print("📦 Import analysis errors: " f"{len(import_errors)}")

    print("🧪 Runtime import checks: " f"{len(runtime_import_results)}")

    print("⚠️ Runtime import errors: " f"{len(runtime_import_errors)}")

    # --------------------------------------------------------
    # STEP 4
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print("STEP 4 - SYSTEM HEALTH")

    print("=" * 60)

    health = health_check()

    print(f"❤️ Status: " f"{health.get('status')}")

    print(f"🐍 Python: " f"{health.get('python')}")

    print(f"🪟 OS: " f"{health.get('os')}")

    print(f"⚙️ Machine: " f"{health.get('machine')}")

    # --------------------------------------------------------
    # STEP 5
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print("STEP 5 - SAFE FIX + DIAGNOSTICS")

    print("=" * 60)

    fixes = safe_auto_fix(
        files,
        syntax_errors,
    )

    print(f"🛠️ Safe formatting fixes: " f"{len(fixes)}")

    # IMPORTANT:
    # If a fix happened, validation is run again.
    if fixes:

        (
            checked,
            syntax_errors,
            import_results,
            combined_import_errors,
        ) = revalidate_after_fixes(files)

    diagnostics = []

    diagnostics.append(run_terminal_command("python --version"))

    diagnostics.append(run_terminal_command("where python"))

    diagnostics.append(run_terminal_command("pip --version"))

    diagnostics.append(run_terminal_command("git status"))

    # --------------------------------------------------------
    # STEP 5B - VS CODE
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print("STEP 5B - VS CODE")

    print("=" * 60)

    vscode_detected = detect_vscode()

    print("🧩 VS Code detected: " f"{vscode_detected}")

    # --------------------------------------------------------
    # STEP 6
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print("STEP 6 - PRODUCTION MONITORING")

    print("=" * 60)

    monitoring_result = run_production_monitoring(
        files,
        health,
    )

    # --------------------------------------------------------
    # STEP 7
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print("STEP 7 - SAFE SELF-HEALING")

    print("=" * 60)

    remediation_result = auto_remediate_alerts(monitoring_result)

    # --------------------------------------------------------
    # STEP 8
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print("STEP 8 - RELEASE / " "DEPLOYMENT GATE")

    print("=" * 60)

    release_checks = release_git_check()

    release_result = prepare_release(
        files,
        health,
        syntax_errors,
        combined_import_errors,
    )

    deployment_result = run_autonomous_orchestrator(
        files,
        health,
        syntax_errors,
        combined_import_errors,
        monitoring_result,
        remediation_result,
        release_result,
    )

    # --------------------------------------------------------
    # PIPELINE STATE
    # --------------------------------------------------------

    pipeline_state = build_pipeline_state(
        files,
        folders,
        syntax_errors,
        combined_import_errors,
        health,
        monitoring_result,
        remediation_result,
        deployment_result,
    )

    pipeline_state["release_prepared"] = release_result.get(
        "prepared",
        False,
    )

    pipeline_state["git"] = release_checks

    pipeline_state["vscode"] = vscode_detected

    pipeline_state["duration_seconds"] = round(
        time.time() - pipeline_start,
        3,
    )

    # --------------------------------------------------------
    # STEP 9
    # --------------------------------------------------------

    print("\n" + "=" * 60)

    print("STEP 9 - CONTROLLED " "CHANGE ENGINE")

    print("=" * 60)

    change_plan = build_change_plan(
        files,
        health,
        syntax_errors,
        combined_import_errors,
        monitoring_result,
        deployment_result,
    )

    pipeline_state = build_final_pipeline_state(
        pipeline_state,
        release_result,
        change_plan,
    )

    pipeline_state["duration_seconds"] = round(
        time.time() - pipeline_start,
        3,
    )

    remember(
        "pipeline_runs",
        pipeline_state,
    )

    save_memory(MEMORY)

    # --------------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------------

    final_health = health_check()

    print("\n" + "=" * 60)

    print("📋 APEX STEPS 1-9 FINAL REPORT")

    print("=" * 60)

    print(f"📁 Files: {len(files)}")

    print(f"📂 Folders: {len(folders)}")

    print(f"🐍 Syntax Errors: " f"{len(syntax_errors)}")

    print(f"📦 Import Errors: " f"{len(combined_import_errors)}")

    print(f"🛠️ Safe Fixes: " f"{len(fixes)}")

    print(f"🖥️ Diagnostics: " f"{len(diagnostics)}")

    print(f"🧩 VS Code: " f"{vscode_detected}")

    print(f"📡 Monitoring: " f"{monitoring_result.get('status')}")

    print(f"🚨 Alerts: " f"{len(monitoring_result.get('alerts', []))}")

    print(f"🩹 Remediation Actions: " f"{len(remediation_result)}")

    print(f"📦 Release Prepared: " f"{release_result.get('prepared', False)}")

    print(f"🎯 Deployment Gate: " f"{deployment_result.get('status')}")

    print(f"🧠 Step 9: " f"{change_plan.get('status')}")

    print(f"❤️ Final Health: " f"{final_health.get('status')}")

    print(f"⏱️ Duration: " f"{pipeline_state['duration_seconds']} sec")

    if change_plan.get("status") == "READY_FOR_APPROVAL":

        print("\n🟢 STEPS 1-9 FOUNDATION READY.")

        print("🔐 Step 9 requires explicit " "approval before source changes.")

        print("🛡️ No source change, Git push, " "or production deployment performed.")

    else:

        print("\n🟡 PIPELINE COMPLETED " "WITH CHECKS REQUIRED.")

    print("=" * 60)


# ============================================================
# ENTRY POINT
# ============================================================


if __name__ == "__main__":
    main()
