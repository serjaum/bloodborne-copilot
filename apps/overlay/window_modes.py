"""Presentation presets for the two overlay window modes."""

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowMode:
    width: int
    height: int
    opacity: float
    always_on_top: bool
    decorated: bool
    resizable: bool


WINDOW_MODES = {
    "compact": WindowMode(
        width=430,
        height=650,
        opacity=0.92,
        always_on_top=True,
        decorated=False,
        resizable=False,
    ),
    "full": WindowMode(
        width=1060,
        height=760,
        opacity=1.0,
        always_on_top=False,
        decorated=True,
        resizable=True,
    ),
}
