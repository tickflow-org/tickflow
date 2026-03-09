"""Custom types and sentinel values for the TickFlow SDK."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, TypeVar, Union

if TYPE_CHECKING:
    import pandas as pd

__all__ = [
    "NOT_GIVEN",
    "NotGiven",
    "Headers",
    "Query",
    "Timeout",
]


class _NotGiven:
    """Sentinel class for distinguishing omitted arguments from None.

    This allows us to differentiate between:
    - `param=None` (explicitly passing None)
    - `param` not provided (using the default)
    """

    __slots__ = ()

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "NOT_GIVEN"


NOT_GIVEN = _NotGiven()

# Type alias for the sentinel
NotGiven = _NotGiven

# Type aliases for common parameter types
Headers = Mapping[str, str]
Query = Mapping[str, Union[str, int, bool, None]]
Timeout = Union[float, None]

# Generic type for response models
T = TypeVar("T")

# Type for DataFrame or raw response
DataFrameType = TypeVar("DataFrameType", bound="pd.DataFrame")


def is_given(value: Any) -> bool:
    """Check if a value was explicitly provided (not NOT_GIVEN)."""
    return not isinstance(value, _NotGiven)


def strip_not_given(params: dict[str, Any]) -> dict[str, Any]:
    """Remove NOT_GIVEN values from a dictionary."""
    return {k: v for k, v in params.items() if is_given(v)}
