"""
Tokenizer Engine — Phase 5.2
-----------------------------------------
Python wrapper for the Rust `titan-core` crate.

Exposes encode/decode/special-token management to the Titan training
pipeline. Falls back to a pure-Python word-level tokenizer if the Rust
extension is not installed.
"""

from __future__ import annotations

from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)

_SPECIAL_TOKENS = {
    "<PAD>": 0,
    "<UNK>": 1,
    "<BOS>": 2,
    "<EOS>": 3,
    "<MASK>": 4,
}


class TokenizerEngine:
    name = "tokenizer_engine"

    def __init__(self) -> None:
        self._rust_available = self._check_rust()
        self._vocab: dict[str, int] = dict(_SPECIAL_TOKENS)
        self._reverse: dict[int, str] = {v: k for k, v in self._vocab.items()}
        self._next_id = len(self._vocab)

    def _check_rust(self) -> bool:
        try:
            import titan_core  # noqa: F401

            return True
        except ImportError:
            return False

    def encode(self, text: str, add_special: bool = True) -> dict[str, Any]:
        if self._rust_available:
            try:
                import titan_core

                ids = titan_core.encode(text)
                return {"ids": ids, "vocab_size": self._vocab_size(), "backend": "rust"}
            except Exception:
                pass
        return self._python_encode(text, add_special=add_special)

    def decode(self, ids: list[int], skip_special: bool = True) -> dict[str, Any]:
        if self._rust_available:
            try:
                import titan_core

                text = titan_core.decode(ids)
                return {"text": text, "backend": "rust"}
            except Exception:
                pass
        return self._python_decode(ids, skip_special=skip_special)

    def add_special_tokens(self, tokens: list[str]) -> dict[str, Any]:
        added = []
        for tok in tokens:
            if tok not in self._vocab:
                self._vocab[tok] = self._next_id
                self._reverse[self._next_id] = tok
                added.append(tok)
                self._next_id += 1
        return {"added": added, "special_tokens": self._list_special_tokens()}

    def _python_encode(self, text: str, add_special: bool = True) -> dict[str, Any]:
        ids: list[int] = []
        if add_special:
            ids.append(_SPECIAL_TOKENS["<BOS>"])
        for ch in text:
            if ch not in self._vocab:
                self._vocab[ch] = self._next_id
                self._reverse[self._next_id] = ch
                self._next_id += 1
            ids.append(self._vocab[ch])
        if add_special:
            ids.append(_SPECIAL_TOKENS["<EOS>"])
        return {"ids": ids, "vocab_size": self._vocab_size(), "backend": "python"}

    def _python_decode(self, ids: list[int], skip_special: bool = True) -> dict[str, Any]:
        chars = []
        for i in ids:
            if skip_special and i in _SPECIAL_TOKENS.values():
                continue
            chars.append(self._reverse.get(i, "<UNK>"))
        return {"text": "".join(chars), "backend": "python"}

    def _vocab_size(self) -> int:
        return len(self._vocab)

    def _list_special_tokens(self) -> dict[str, int]:
        return dict(_SPECIAL_TOKENS)


tokenizer_engine = TokenizerEngine()
