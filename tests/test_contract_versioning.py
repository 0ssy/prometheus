import pytest

from contracts.versioning import is_contract_compatible, validate_contract_compatibility


def test_contract_compatibility_same_major_allows_newer_runtime():
    assert is_contract_compatible("1.0.0", "1.2.3")
    assert is_contract_compatible("1.2.0", "1.2.3")


def test_contract_compatibility_rejects_major_mismatch():
    assert not is_contract_compatible("2.0.0", "1.9.9")


def test_contract_compatibility_rejects_newer_required_minor_patch():
    assert not is_contract_compatible("1.3.0", "1.2.9")
    assert not is_contract_compatible("1.2.4", "1.2.3")


def test_validate_contract_compatibility_raises_on_mismatch():
    with pytest.raises(RuntimeError, match="Incompatible contract version"):
        validate_contract_compatibility("2.0.0", "1.0.0")
