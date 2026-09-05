"""Offline translation via Argos Translate.

Argos runs a local neural MT model per language pair - there is no per-request
call to a cloud AI API. The first time a given language pair is requested, its
model package is fetched once from the Argos package index and cached on disk;
every translation after that runs entirely offline.
"""
from __future__ import annotations

import threading

import argostranslate.package
import argostranslate.translate

_lock = threading.Lock()
_installed_pairs: set[tuple[str, str]] = set()


def ensure_language_pair(from_code: str, to_code: str) -> None:
    if from_code == to_code:
        return
    with _lock:
        if (from_code, to_code) in _installed_pairs:
            return
        if _translation_installed(from_code, to_code):
            _installed_pairs.add((from_code, to_code))
            return
        argostranslate.package.update_package_index()
        available = argostranslate.package.get_available_packages()
        match = next((p for p in available if p.from_code == from_code and p.to_code == to_code), None)
        if match is None:
            raise ValueError(f"No offline translation model available for {from_code} -> {to_code}")
        argostranslate.package.install_from_path(match.download())
        _installed_pairs.add((from_code, to_code))


def _translation_installed(from_code: str, to_code: str) -> bool:
    languages = argostranslate.translate.get_installed_languages()
    source = next((l for l in languages if l.code == from_code), None)
    target = next((l for l in languages if l.code == to_code), None)
    if source is None or target is None:
        return False
    return source.get_translation(target) is not None


def translate_text(text: str, from_code: str, to_code: str) -> str:
    if from_code == to_code or not text.strip():
        return text
    ensure_language_pair(from_code, to_code)
    return argostranslate.translate.translate(text, from_code, to_code)
