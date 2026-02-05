"""
MODULE: tools.lint_module_contracts
RESPONSIBILITY: Linting tool to enforce Module Contract compliance.
ALLOWED: pathlib, sys, ast.
FORBIDDEN: None.
ERRORS: None.
"""
from pathlib import Path
import sys
import ast

REQUIRED_SECTIONS = {
    "MODULE:",
    "RESPONSIBILITY:",
    "ALLOWED:",
    "FORBIDDEN:",
    "ERRORS:",
}

EXCLUDED_DIRS = {
    "__pycache__",
    "tests",
    "sandbox",
    ".venv",
    "venv",
    ".git",
    ".idea"
}

EXCLUDED_FILES = {
    "__init__.py",
    "main.py",
    "setup.py",
    "conftest.py"
}


def is_excluded(path: Path) -> bool:
    return (
        any(part in EXCLUDED_DIRS for part in path.parts)
        or path.name in EXCLUDED_FILES
    )


def get_module_docstring(path: Path) -> str | None:
    try:
        # Pylint/Ast sometimes fails on empty files or encoding
        text = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(text)
        return ast.get_docstring(tree)
    except Exception:
        return None


def check_contract(path: Path) -> list[str]:
    errors: list[str] = []

    docstring = get_module_docstring(path)
    if not docstring:
        return [f"{path}: missing module docstring (Module Contract required)"]

    missing = [
        section for section in REQUIRED_SECTIONS
        if section not in docstring
    ]

    if missing:
        errors.append(
            f"{path}: missing contract sections: {', '.join(missing)}"
        )

    return errors


def main() -> int:
    root = Path.cwd()
    py_files = root.rglob("*.py")

    all_errors: list[str] = []

    count = 0
    for path in py_files:
        # Пропускаем файлы в корне если они в исключениях или скрытых папках
        if is_excluded(path):
            continue

        if path.stat().st_size < 50:
            continue

        # Относительный путь для красоты вывода
        try:
            rel_path = path.relative_to(root)
        except ValueError:
            rel_path = path

        contract_errors = check_contract(path)
        if contract_errors:
            all_errors.extend(contract_errors)
        
        count += 1

    print(f"Checked {count} modules.")

    if all_errors:
        print("\n❌ MODULE CONTRACT VIOLATIONS:\n")
        for error in all_errors:
            print(f"  - {error}")
        print("\nVIOLATION: Every business module MUST have a valid contract in docstring.")
        return 1

    print("✅ All modules contain valid contracts")
    return 0


if __name__ == "__main__":
    sys.exit(main())
