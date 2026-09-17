"""
Automated tests for cli.py.

Run with:
    pip install pytest click pyflakes
    pytest -v

Structure:
- Unit tests for the pure logic helpers, using pytest's `tmp_path` to build
  small, purpose-built directories per test (fast, and each test is
  self-explanatory without needing a big shared fixture).
- Integration tests for each CLI flag, using Click's CliRunner to invoke the
  real `cli()` command and check its printed output and exit code.
- Several tests are explicit regression tests for bugs found and fixed
  during development (division by zero, missing package.json crashing,
  node_modules not being pruned, etc.) - each one is labeled as such.
"""
import ast
import json
import subprocess

import pytest
from click.testing import CliRunner

from cli import (
    cli,
    cyclomatic_complexity,
    max_nesting_depth,
    function_length,
    hasGit,
    folder_size,
    emptyFiles,
    dupFiles,
    countLines,
)


# ---------------------------------------------------------------------------
# Unit tests: AST-based complexity helpers
# ---------------------------------------------------------------------------

def _first_function(source):
    tree = ast.parse(source)
    return tree.body[0]


def test_cyclomatic_complexity_no_branches():
    func = _first_function("def f():\n    return 1\n")
    assert cyclomatic_complexity(func) == 1


def test_cyclomatic_complexity_with_if():
    func = _first_function("def f(x):\n    if x:\n        return 1\n    return 0\n")
    assert cyclomatic_complexity(func) == 2


def test_cyclomatic_complexity_with_boolop():
    # base 1 + 1 (if) + 2 (a 3-value BoolOp adds len(values)-1 = 2)
    func = _first_function(
        "def f(a, b, c):\n    if a and b and c:\n        return 1\n    return 0\n"
    )
    assert cyclomatic_complexity(func) == 4


def test_cyclomatic_complexity_with_except_and_comprehension():
    src = (
        "def f(items):\n"
        "    try:\n"
        "        return [x for x in items if x]\n"
        "    except ValueError:\n"
        "        return []\n"
    )
    func = _first_function(src)
    # base 1 + 1 (try) + 1 (except) + 1 (comprehension) + 1 (comprehension's if) = 5
    assert cyclomatic_complexity(func) == 5


def test_max_nesting_depth_flat_function():
    func = _first_function("def f():\n    return 1\n")
    assert max_nesting_depth(func) == 0


def test_max_nesting_depth_counts_nested_blocks():
    src = "def f(x):\n    for i in x:\n        if i:\n            return i\n    return None\n"
    func = _first_function(src)
    assert max_nesting_depth(func) == 2


def test_max_nesting_depth_ignores_nested_function_body():
    src = (
        "def outer():\n"
        "    def inner():\n"
        "        if True:\n"
        "            if True:\n"
        "                pass\n"
        "    return inner\n"
    )
    outer = _first_function(src)
    assert max_nesting_depth(outer) == 0


def test_function_length_simple():
    src = "def f():\n    x = 1\n    y = 2\n    return x + y\n"
    func = _first_function(src)
    assert function_length(func) == 4


def test_function_length_includes_decorator_line():
    src = "@staticmethod\ndef f():\n    return 1\n"
    func = _first_function(src)
    assert function_length(func) == 3


# ---------------------------------------------------------------------------
# Unit tests: filesystem helpers
# ---------------------------------------------------------------------------

def test_hasGit_true_when_dot_git_exists(tmp_path):
    (tmp_path / ".git").mkdir()
    assert hasGit(str(tmp_path)) is True


def test_hasGit_false_when_missing(tmp_path):
    assert hasGit(str(tmp_path)) is False


def test_folder_size_sums_file_bytes(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"x" * 100)
    (tmp_path / "b.txt").write_bytes(b"y" * 50)
    assert folder_size(str(tmp_path)) == 150


def test_folder_size_recurses_into_subdirs(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "a.txt").write_bytes(b"1" * 10)
    (sub / "b.txt").write_bytes(b"2" * 20)
    assert folder_size(str(tmp_path)) == 30


def test_countLines_counts_newline_separated_lines(tmp_path):
    f = tmp_path / "sample.py"
    f.write_text("a\nb\nc\n")
    assert countLines(str(f)) == 3


def test_emptyFiles_counts_zero_byte_files(tmp_path):
    (tmp_path / "empty.py").write_text("")
    (tmp_path / "nonempty.py").write_text("x = 1\n")
    assert emptyFiles(str(tmp_path)) == 1


def test_emptyFiles_skips_node_modules(tmp_path):
    """Regression test: emptyFiles used to walk into node_modules/.git unfiltered."""
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "empty.js").write_text("")
    (tmp_path / "real.py").write_text("x = 1\n")
    assert emptyFiles(str(tmp_path)) == 0


def test_dupFiles_detects_same_filename_in_different_dirs(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "config.json").write_text("{}")
    (b / "config.json").write_text("{}")
    assert dupFiles(str(tmp_path)) == 1


def test_dupFiles_no_false_positive_across_extensions(tmp_path):
    """helpers.py and helpers.js should NOT count as duplicates (exact filename match only)."""
    (tmp_path / "helpers.py").write_text("x = 1\n")
    (tmp_path / "helpers.js").write_text("const x = 1;\n")
    assert dupFiles(str(tmp_path)) == 0


def test_dupFiles_skips_git_dir(tmp_path):
    """Regression test: dupFiles used to walk into .git unfiltered."""
    (tmp_path / "app.py").write_text("x = 1\n")
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "app.py").write_text("irrelevant")
    assert dupFiles(str(tmp_path)) == 0


# ---------------------------------------------------------------------------
# Integration tests: -i / --info
# ---------------------------------------------------------------------------

class TestDashI:
    def test_reports_file_dir_and_language_counts(self, tmp_path):
        (tmp_path / "main.py").write_text("print('hi')\n")
        (tmp_path / "app.js").write_text("console.log('hi');\n")
        result = CliRunner().invoke(cli, ["-i", str(tmp_path)])
        assert result.exit_code == 0
        assert "Total # Files:2" in result.output
        assert "Python: 1 files" in result.output
        assert "JavaScript: 1 files" in result.output
        assert "Git Repository: No" in result.output

    def test_detects_git_repository(self, tmp_path):
        (tmp_path / ".git").mkdir()
        result = CliRunner().invoke(cli, ["-i", str(tmp_path)])
        assert result.exit_code == 0
        assert "Git Repository: Yes" in result.output

    def test_rejects_a_file_path(self, tmp_path):
        """Regression test: -i used to silently accept a file instead of a directory."""
        f = tmp_path / "readme.txt"
        f.write_text("hi")
        result = CliRunner().invoke(cli, ["-i", str(f)])
        assert result.exit_code != 0
        assert "is a file" in result.output


# ---------------------------------------------------------------------------
# Integration tests: -s / --size
# ---------------------------------------------------------------------------

class TestDashS:
    def test_reports_loc_and_largest_file(self, tmp_path):
        (tmp_path / "a.py").write_text("x = 1\ny = 2\n")
        (tmp_path / "b.py").write_text("z = 3\n")
        result = CliRunner().invoke(cli, ["-s", str(tmp_path)])
        assert result.exit_code == 0
        assert "Python: 3 lines" in result.output
        assert "Largest File: a.py (2 lines)" in result.output

    def test_empty_directory_does_not_crash(self, tmp_path):
        """Regression test: used to raise ZeroDivisionError on an empty directory."""
        result = CliRunner().invoke(cli, ["-s", str(tmp_path)])
        assert result.exit_code == 0
        assert result.exception is None
        assert "Average File Size: 0 lines" in result.output


# ---------------------------------------------------------------------------
# Integration tests: -g / --git
# ---------------------------------------------------------------------------

class TestDashG:
    def test_reports_status_for_a_real_repo(self, tmp_path):
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
        (tmp_path / "file.txt").write_text("hello\n")
        subprocess.run(["git", "add", "file.txt"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "initial commit"], cwd=tmp_path, check=True)

        result = CliRunner().invoke(cli, ["-g", str(tmp_path)])
        assert result.exit_code == 0
        assert "Message: initial commit" in result.output

    def test_non_git_directory_does_not_crash(self, tmp_path):
        """Regression test: used to run git commands against a non-repo and print garbage."""
        result = CliRunner().invoke(cli, ["-g", str(tmp_path)])
        assert result.exit_code == 0
        assert result.exception is None
        assert "is not a git repository" in result.output


# ---------------------------------------------------------------------------
# Integration tests: -d / --dep
# ---------------------------------------------------------------------------

class TestDashA:
    def test_missing_package_json_gives_clean_error(self, tmp_path):
        """Regression test: used to raise an unhandled Exception with a full traceback."""
        result = CliRunner().invoke(cli, ["-d", str(tmp_path)])
        assert result.exit_code == 1
        assert result.exception is None or isinstance(result.exception, SystemExit)
        assert "No package.json found" in result.output

    def test_missing_node_modules_does_not_crash(self, tmp_path):
        """Regression test: used to raise FileNotFoundError on os.listdir('')."""
        (tmp_path / "package.json").write_text(
            json.dumps({"dependencies": {"lodash": "^4.0.0"}, "devDependencies": {}})
        )
        result = CliRunner().invoke(cli, ["-d", str(tmp_path)])
        assert result.exit_code == 0
        assert "Production: 1" in result.output
        assert "node_modules not found" in result.output

    def test_ranks_only_declared_and_installed_packages_by_size(self, tmp_path):
        (tmp_path / "package.json").write_text(
            json.dumps(
                {
                    "dependencies": {"small-pkg": "^1.0.0", "big-pkg": "^1.0.0"},
                    "devDependencies": {},
                }
            )
        )
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "small-pkg").mkdir()
        (nm / "small-pkg" / "index.js").write_bytes(b"x" * 100)
        (nm / "big-pkg").mkdir()
        (nm / "big-pkg" / "index.js").write_bytes(b"x" * 5000)
        # an installed-but-undeclared package should never be reported
        (nm / "not-declared").mkdir()
        (nm / "not-declared" / "index.js").write_bytes(b"x" * 999999)

        result = CliRunner().invoke(cli, ["-d", str(tmp_path)])
        assert result.exit_code == 0
        assert "not-declared" not in result.output

        # Only look within the "Largest Packages" section - the dependency
        # count line above it also mentions each package name (it dumps the
        # raw dependencies dict), which would otherwise give a false match.
        ranking = result.output.split("Largest Packages")[1]
        big_pos = ranking.find("big-pkg")
        small_pos = ranking.find("small-pkg")
        assert big_pos != -1 and small_pos != -1
        assert big_pos < small_pos  # larger package listed first


# ---------------------------------------------------------------------------
# Integration tests: -h / --health
# ---------------------------------------------------------------------------

class TestDashH:
    def test_reports_found_and_not_found(self, tmp_path):
        (tmp_path / "README.md").write_text("# hi\n")
        (tmp_path / ".gitignore").write_text("node_modules\n")
        result = CliRunner().invoke(cli, ["-h", str(tmp_path)])
        assert result.exit_code == 0
        assert "README: Found" in result.output
        assert "LICENSE: Not Found" in result.output
        assert "Git Ignore: Found" in result.output
        assert ".env file: Not Found" in result.output
        assert "Package JSON: Not Found" in result.output

    def test_ignores_package_json_inside_node_modules(self, tmp_path):
        """Regression test: fileCheck used to walk into node_modules unfiltered."""
        nm = tmp_path / "node_modules" / "some-pkg"
        nm.mkdir(parents=True)
        (nm / "package.json").write_text("{}")
        result = CliRunner().invoke(cli, ["-h", str(tmp_path)])
        assert result.exit_code == 0
        assert "Package JSON: Not Found" in result.output


# ---------------------------------------------------------------------------
# Integration tests: -t / --test
# ---------------------------------------------------------------------------

class TestDashT:
    def test_reports_metrics_for_python_files(self, tmp_path):
        (tmp_path / "sample.py").write_text(
            "def f(x):\n    if x:\n        return 1\n    return 0\n"
        )
        result = CliRunner().invoke(cli, ["-t", str(tmp_path)])
        assert result.exit_code == 0
        assert "Files scanned:     1" in result.output
        assert "Functions found:   1" in result.output

    def test_no_python_files_reports_cleanly(self, tmp_path):
        (tmp_path / "app.js").write_text("console.log('hi');\n")
        result = CliRunner().invoke(cli, ["-t", str(tmp_path)])
        assert result.exit_code == 0
        assert "No functions found." in result.output
