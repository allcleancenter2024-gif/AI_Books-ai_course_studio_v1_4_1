from __future__ import annotations

import codecs
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

from fastapi import HTTPException
from PIL import Image
from pypdf import PdfReader

from ..config import EXTRACTED_TEXT_LIMIT

ALLOWED_EXTENSIONS = {".md", ".markdown", ".txt", ".html", ".htm", ".pdf", ".pptx", ".png", ".jpg", ".jpeg", ".webp"}


class BoundedText:
    def __init__(self, limit: int = EXTRACTED_TEXT_LIMIT):
        self.limit = limit
        self.parts: list[str] = []
        self.length = 0

    def add(self, value: str):
        if self.length >= self.limit or not value:
            return
        value = value[: self.limit - self.length]
        self.parts.append(value)
        self.length += len(value)

    def value(self) -> str:
        return "".join(self.parts)


class StreamingHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.output = BoundedText()
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "nav", "footer"}:
            self.skip += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "nav", "footer"} and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.output.add(data.strip() + "\n")


def _encoding(path: Path) -> str:
    head = path.open("rb").read(4096)
    for enc in ("utf-8-sig", "utf-8", "cp949", "euc-kr"):
        try:
            head.decode(enc)
            return enc
        except UnicodeDecodeError:
            pass
    return "utf-8"


def _text(path: Path, html: bool = False) -> str:
    decoder = codecs.getincrementaldecoder(_encoding(path))(errors="replace")
    parser = StreamingHTML() if html else None
    output = BoundedText()
    with path.open("rb") as stream:
        while output.length < output.limit:
            raw = stream.read(1024 * 1024)
            if not raw:
                break
            value = decoder.decode(raw)
            if parser:
                parser.feed(value)
                output = parser.output
            else:
                output.add(value)
    return output.value()


def parse_file(path: Path, progress=lambda current, total, message: None) -> tuple[str, dict]:
    ext = path.suffix.lower()
    meta = {"extension": ext, "size": path.stat().st_size, "text_truncated_at": EXTRACTED_TEXT_LIMIT}
    if ext in {".md", ".markdown", ".txt"}:
        return _text(path), meta
    if ext in {".html", ".htm"}:
        return _text(path, html=True), meta
    if ext == ".pdf":
        reader, output = PdfReader(str(path)), BoundedText()
        total = len(reader.pages)
        meta["pages"] = total
        for index, page in enumerate(reader.pages):
            progress(index + 1, total, f"PDF {index + 1}/{total}쪽 분석 중")
            try:
                output.add(f"[Page {index + 1}]\n{page.extract_text() or ''}\n\n")
            except Exception:
                output.add(f"[Page {index + 1}] [텍스트 추출 실패]\n\n")
            if output.length >= output.limit:
                break
        return output.value(), meta
    if ext == ".pptx":
        output = BoundedText()
        with zipfile.ZipFile(path) as archive:
            names = sorted((n for n in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)), key=lambda n: int(re.search(r"\d+", Path(n).stem).group()))
            meta["slides"] = len(names)
            for index, name in enumerate(names):
                progress(index + 1, len(names), f"PPTX {index + 1}/{len(names)}장 분석 중")
                root = ElementTree.parse(archive.open(name)).getroot()
                chunks = [node.text for node in root.iter() if node.tag.endswith("}t") and node.text]
                output.add(f"[Slide {index + 1}]\n" + "\n".join(chunks) + "\n\n")
                root.clear()
                if output.length >= output.limit:
                    break
        return output.value(), meta
    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        with Image.open(path) as image:
            meta.update(width=image.width, height=image.height, format=image.format or ext[1:])
        return "", meta
    raise HTTPException(400, f"지원하지 않는 파일 형식입니다: {ext}")
