"""Tests de validación de semilla de génesis."""

import pytest

from main.bootstrap.genesis_seed import require_genesis_seed


def test_require_genesis_seed_accepts_non_empty():
    assert require_genesis_seed("mi-semilla") == "mi-semilla"
    assert require_genesis_seed("  padded  ") == "padded"


def test_require_genesis_seed_rejects_empty(monkeypatch):
    monkeypatch.setattr("sys.exit", lambda code: (_ for _ in ()).throw(SystemExit(code)))
    with pytest.raises(SystemExit) as exc:
        require_genesis_seed(None)
    assert exc.value.code == 2
    with pytest.raises(SystemExit):
        require_genesis_seed("   ")
