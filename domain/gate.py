"""The effort gate: the four levels a plan may name."""

from enum import StrEnum


class Gate(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"
