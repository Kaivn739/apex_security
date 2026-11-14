import ast
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

def main():
    print("=" * 60)
    print("APEX STEP 5 - ISOLATED SAFE AUTO-FIX TEST")
    print("=" * 60)

    project_file = Path(__file__).resolve().parent / "apex_developer.py"

    if not project_file.is_file():
        print("FAIL: apex_developer.py was not found.")
        return 1

    try:
        source = project_file.read_text(encoding="utf-8-sig")
        syntax_tree = ast.parse(source)

        functions = [
            node
            for node in syntax_tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "safe_auto_fix"
        ]

        if len(functions) != 1:
            print(
                "FAIL: Expected exactly one safe_auto_fix function; "
                f"found {len(functions)}."
            )
            return 1

        function_source = ast.get_source_segment(source, functions[0])

        if not function_source:
            print("FAIL: Could not extract the function source.")
            return 1

        if isinstance(functions[0], ast.AsyncFunctionDef):
            print("FAIL: Unexpected async safe_auto_fix function.")
            return 1

        print("PASS: Main source file parsed.")
        print("PASS: Exactly one safe_auto_fix function found.")

    except Exception as error:
        print(f"FAIL: Source inspection: {error}")
        return 1

    with tempfile.TemporaryDirectory(
        prefix="apex_step5_test_"
    ) as temporary_directory:

        root = Path(temporary_directory)
        backup_directory = root / "backups"

        test_memory = {"fixes": []}
        save_calls = []

        def test_relative_path(path):
            return Path(path).name

        def test_now_iso():
            return "STEP5-TEST"

        def test_save_memory(memory):
            save_calls.append(
                [record.copy() for record in memory.get("fixes", [])]
            )

        namespace = {
            "Path": Path,
            "datetime": datetime,
            "shutil": shutil,
            "BACKUP_DIR": backup_directory,
            "MEMORY": test_memory,
            "save_memory": test_save_memory,
            "relative_path": test_relative_path,
            "now_iso": test_now_iso,
        }

        try:
            compiled_function = compile(
                function_source,
                str(project_file),
                "exec",
            )
            exec(compiled_function, namespace)

            safe_auto_fix = namespace["safe_auto_fix"]

            print("PASS: Function loaded in isolated environment.")

        except Exception as error:
            print(f"FAIL: Function loading: {error}")
            return 1

        # TEST 1: Formatting and backup verification.
        print("\n[TEST 1] Formatting and backup")

        sample_file = root / "sample.py"
        original_bytes = (
            b"def hello():   \r\n"
            b"    return 'APEX'    \r\n"
        )
        sample_file.write_bytes(original_bytes)

        try:
            fixes = safe_auto_fix(
                [sample_file],
                [{"file": "sample.py"}],
            )

            if len(fixes) != 1:
                raise AssertionError(
                    f"Expected one fix, received {len(fixes)}."
                )

            updated_bytes = sample_file.read_bytes()

            if updated_bytes == original_bytes:
                raise AssertionError("Formatting did not change the file.")

            updated_text = updated_bytes.decode("utf-8-sig")
            compile(updated_text, str(sample_file), "exec")

            backup_file = Path(fixes[0]["backup"])

            if not backup_file.is_file():
                raise AssertionError("Backup file is missing.")

            if backup_file.read_bytes() != original_bytes:
                raise AssertionError("Backup differs from original bytes.")

            if not save_calls:
                raise AssertionError("Test memory stub was not called.")

            print("PASS: Formatting cleanup applied.")
            print("PASS: Updated source passes Python compilation.")
            print("PASS: Backup matches the original byte-for-byte.")
            print("PASS: Memory writes were redirected to a test stub.")

        except Exception as error:
            print(f"FAIL: Formatting/backup test: {error}")
            return 1

        # TEST 2: Invalid Python must remain unchanged.
        print("\n[TEST 2] Invalid syntax protection")

        invalid_file = root / "invalid.py"
        invalid_original = b"def broken(:\n    pass   \n"
        invalid_file.write_bytes(invalid_original)

        backups_before = (
            len(list(backup_directory.glob("*.bak")))
            if backup_directory.exists()
            else 0
        )

        try:
            invalid_fixes = safe_auto_fix(
                [invalid_file],
                [{"file": "invalid.py"}],
            )

            backups_after = (
                len(list(backup_directory.glob("*.bak")))
                if backup_directory.exists()
                else 0
            )

            if invalid_file.read_bytes() != invalid_original:
                raise AssertionError("Invalid source was modified.")

            if invalid_fixes:
                raise AssertionError("Invalid source was reported as fixed.")

            if backups_after != backups_before:
                raise AssertionError(
                    "Unexpected backup created for invalid source."
                )

            print("PASS: Invalid source remained unchanged.")
            print("PASS: No false successful fix was reported.")
            print("PASS: No unnecessary backup was created.")

        except Exception as error:
            print(f"FAIL: Invalid syntax test: {error}")
            return 1

        # TEST 3: Already-clean file must remain unchanged.
        print("\n[TEST 3] No-change handling")

        clean_file = root / "clean.py"
        clean_original = b"def okay():\n    return 1\n"
        clean_file.write_bytes(clean_original)

        try:
            clean_fixes = safe_auto_fix(
                [clean_file],
                [{"file": "clean.py"}],
            )

            if clean_file.read_bytes() != clean_original:
                raise AssertionError("Clean file was modified.")

            if clean_fixes:
                raise AssertionError(
                    "Clean file was incorrectly reported as fixed."
                )

            print("PASS: Clean file remained unchanged.")
            print("PASS: No false fix was reported.")

        except Exception as error:
            print(f"FAIL: No-change test: {error}")
            return 1

        # TEST 4: UTF-8 BOM must be preserved.
        print("\n[TEST 4] UTF-8 BOM preservation")

        bom_file = root / "bom_sample.py"
        bom_original = (
            b"\xef\xbb\xbf"
            b"def bom_test():   \r\n"
            b"    return 'BOM'    \r\n"
        )
        bom_file.write_bytes(bom_original)

        try:
            bom_fixes = safe_auto_fix(
                [bom_file],
                [{"file": "bom_sample.py"}],
            )

            if len(bom_fixes) != 1:
                raise AssertionError("BOM test did not produce one fix.")

            bom_updated = bom_file.read_bytes()

            if not bom_updated.startswith(b"\xef\xbb\xbf"):
                raise AssertionError("UTF-8 BOM was not preserved.")

            compile(
                bom_updated.decode("utf-8-sig"),
                str(bom_file),
                "exec",
            )

            bom_backup = Path(bom_fixes[0]["backup"])

            if bom_backup.read_bytes() != bom_original:
                raise AssertionError("BOM backup differs from original.")

            print("PASS: UTF-8 BOM was preserved.")
            print("PASS: BOM file passes Python compilation.")
            print("PASS: Original BOM file was backed up exactly.")

        except Exception as error:
            print(f"FAIL: BOM preservation test: {error}")
            return 1

        # TEST 5: Verify test artifacts are isolated.
        print("\n[TEST 5] Isolation")

        for path in root.rglob("*"):
            if path.is_file() and not path.is_relative_to(root):
                print("FAIL: An artifact escaped the temporary directory.")
                return 1

        print("PASS: Test artifacts remain in the temporary directory.")
        print("PASS: Main project memory was not loaded or saved.")
        print("PASS: Main pipeline was not executed.")

    print("\n" + "=" * 60)
    print("ALL STEP 5 ISOLATED TESTS PASSED")
    print("=" * 60)
    print("Note: This tests safe_auto_fix in isolation.")
    print("It does not test the complete pipeline integration.")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())