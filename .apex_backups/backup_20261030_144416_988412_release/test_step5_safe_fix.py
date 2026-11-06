import ast
import tempfile
from pathlib import Path


def test_format_cleanup_preserves_syntax():
    original = "def hello():   \n" "    return 'APEX'    \n"

    with tempfile.TemporaryDirectory(prefix="apex_step5_test_") as temp_dir:
        test_file = Path(temp_dir) / "sample.py"
        test_file.write_text(original, encoding="utf-8")

        before = test_file.read_bytes()
        source = before.decode("utf-8")

        candidate = "\n".join(line.rstrip() for line in source.split("\n"))
        candidate = candidate.rstrip("\n") + "\n"

        # دڵنیابوون لەوەی کاندیدەکە سینتاکسی دروستە
        ast.parse(candidate)

        # تەنها فایلە تاقیکارییەکە دەگۆڕین
        test_file.write_text(candidate, encoding="utf-8")

        after = test_file.read_bytes()
        ast.parse(after.decode("utf-8"))

        assert after != before, "فایلە تاقیکارییەکە نەگۆڕا."
        assert "return 'APEX'" in after.decode("utf-8")

        print("PASS: Formatting cleanup test")
        print("PASS: Candidate syntax validation")
        print("PASS: Only the temporary test file was modified")


if __name__ == "__main__":
    test_format_cleanup_preserves_syntax()
