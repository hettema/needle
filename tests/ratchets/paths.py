from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
BACKEND_PACKAGES = ["domain", "board", "infrastructure", "api"]
FRONTEND_SRC = REPO / "frontend" / "src"
UI = FRONTEND_SRC / "components" / "ui"


def python_files(*packages: str) -> list[Path]:
    files: list[Path] = []
    for package in packages:
        files += sorted((REPO / package).rglob("*.py"))
    return files


def frontend_files(root: Path = FRONTEND_SRC) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.suffix in {".ts", ".tsx", ".css"} and p.is_file())
