"""Docstring-based tests for placeholder strategic modules."""

import doctest

import diplomacy
import siege
import weather


def test_doctests() -> None:
    """Ensure placeholder modules expose documented structures."""

    for module in (siege, diplomacy, weather):
        result = doctest.testmod(module)
        assert result.failed == 0
