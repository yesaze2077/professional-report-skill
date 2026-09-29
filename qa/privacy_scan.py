#!/usr/bin/env python3
"""Conservative public-package scan; does not claim exhaustive privacy safety."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
import io
import tempfile
import zipfile
import zlib
from pathlib import Path

PATTERNS = {
    "credential": re.compile(r"(?:sk-[A-Za-z0-9_-]{20,}|gh[pousr]_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)"),
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "phone": re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)"),
    "absolute_path": re.compile(r"(?:/Us" + r"ers/|/ho" + r"me/|C:\\Us" + r"ers\\)[^\s<>'\"]+"),
}
TEXT_EXT = {".md", ".py", ".json", ".css", ".html", ".yaml", ".yml", ".txt", ""}
SKIP = {".git", "__pycache__"}
MAX_MEMBER_BYTES = 30_000_000


def pdf_text(data: bytes) -> str:
    if shutil.which("pdftotext"):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as tmp:
            tmp.write(data);tmp.flush()
            result = subprocess.run(["pdftotext", tmp.name, "-"], capture_output=True, text=True, check=True)
            return result.stdout
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("PDF 未扫描（需要 pdftotext 或 pypdf）") from exc
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(data)).pages)


def png_metadata(data: bytes) -> str:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise RuntimeError("PNG 头无效")
    parts=[];offset=8
    while offset+12<=len(data):
        size=int.from_bytes(data[offset:offset+4],"big")
        kind=data[offset+4:offset+8]
        if size>MAX_MEMBER_BYTES or offset+12+size>len(data): raise RuntimeError("PNG 块长度异常")
        chunk=data[offset+8:offset+8+size]
        if kind in {b"tEXt",b"iTXt",b"zTXt",b"eXIf"}:
            if kind==b"zTXt":
                try: chunk=chunk.split(b"\x00",2)[-1];chunk=zlib.decompress(chunk)
                except (zlib.error,ValueError): raise RuntimeError("PNG 压缩元数据不可读")
            parts.append(chunk.decode("latin1",errors="ignore"))
        offset+=12+size
        if kind==b"IEND":break
    return "\n".join(parts)


def inspect_bytes(name: str, data: bytes, findings: list[str]) -> None:
    suffix=Path(name).suffix.lower()
    try:
        if suffix==".pdf": text=pdf_text(data)+"\n"+data.decode("latin1",errors="ignore")
        elif suffix==".png": text=png_metadata(data)+"\n"+data.decode("latin1",errors="ignore")
        elif suffix in TEXT_EXT: text=data.decode("utf-8",errors="ignore")
        elif suffix in {".jpg",".jpeg",".webp",".svg"}: text=data.decode("latin1",errors="ignore")
        else:return
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        findings.append(f"{name}: {exc}")
        return
    for label, pattern in PATTERNS.items():
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            findings.append(f"{name}:{line}: {label}")


def scan(root: Path) -> list[str]:
    findings: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP for part in path.parts):
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        name=str(path.relative_to(root))
        if path.suffix.lower()==".zip":
            try:
                with zipfile.ZipFile(path) as archive:
                    for item in archive.infolist():
                        if item.is_dir():continue
                        if item.file_size>MAX_MEMBER_BYTES:
                            findings.append(f"{name}:{item.filename}: 条目过大，未扫描");continue
                        inspect_bytes(name+":"+item.filename, archive.read(item), findings)
            except zipfile.BadZipFile: findings.append(f"{name}: ZIP 损坏，未扫描")
            continue
        inspect_bytes(name,path.read_bytes(),findings)
    return findings


if __name__ == "__main__":
    base = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    findings = scan(base)
    if findings:
        print("\n".join(findings))
        raise SystemExit(1)
    print("privacy scan: no configured patterns found")
