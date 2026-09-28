#!/usr/bin/env python3
"""Conservative public-package scan; does not claim exhaustive privacy safety."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

PATTERNS = {
    "credential": re.compile(r"(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"),
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "phone": re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)"),
    "absolute_path": re.compile(r"(?:/Users/|/home/|C:\\Users\\)[^\s<>'\"]+"),
}
TEXT_EXT = {".md", ".py", ".json", ".css", ".html", ".yaml", ".yml", ".txt", ""}
SKIP = {".git", "__pycache__"}


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP for part in path.parts):
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        if path.suffix.lower() == ".pdf":
            if shutil.which("pdftotext"):
                result = subprocess.run(["pdftotext", str(path), "-"], capture_output=True, text=True, check=True)
                text = result.stdout
            else:
                try:
                    from pypdf import PdfReader
                except ImportError:
                    findings.append(f"{path.relative_to(root)}: PDF 未扫描（需要 pdftotext 或 pypdf）")
                    continue
                reader = PdfReader(path)
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            text += "\n" + path.read_bytes().decode("latin1", errors="ignore")
        elif path.suffix.lower() in TEXT_EXT:
            text = path.read_text(encoding="utf-8", errors="ignore")
        else:
            continue
        for label, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{path.relative_to(root)}:{line}: {label}")
    return findings


if __name__ == "__main__":
    base = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    findings = scan(base)
    if findings:
        print("\n".join(findings))
        raise SystemExit(1)
    print("privacy scan: no configured patterns found")
