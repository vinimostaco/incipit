"""Modelos de dados compartilhados entre extração, TTS e API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Paragraph(BaseModel):
    index: int
    text: str


class Chapter(BaseModel):
    index: int
    title: str | None = None
    paragraphs: list[Paragraph] = Field(default_factory=list)


class Book(BaseModel):
    title: str | None = None
    author: str | None = None
    source_format: str  # "pdf" | "epub"
    chapters: list[Chapter] = Field(default_factory=list)

    @property
    def paragraph_count(self) -> int:
        return sum(len(c.paragraphs) for c in self.chapters)


class ExtractRequest(BaseModel):
    path: str


class TTSRequest(BaseModel):
    text: str
    engine: str = "piper"
    voice: str | None = None
    language: str = "pt"
    speed: float = 1.0
