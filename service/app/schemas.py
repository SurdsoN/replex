"""Shared data structures passed between extraction, translation, and docx rendering."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    size: float


@dataclass
class Line:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float
    size: float


@dataclass
class ParagraphBlock:
    text: str
    bbox: tuple[float, float, float, float]  # x0, top, x1, bottom
    size: float
    translated_text: str | None = None


@dataclass
class TableBlock:
    bbox: tuple[float, float, float, float]
    rows: list[list[str]]
    translated_rows: list[list[str]] | None = None


@dataclass
class Page:
    width: float
    height: float
    paragraphs: list[ParagraphBlock] = field(default_factory=list)
    tables: list[TableBlock] = field(default_factory=list)


@dataclass
class ExtractedDocument:
    pages: list[Page] = field(default_factory=list)
