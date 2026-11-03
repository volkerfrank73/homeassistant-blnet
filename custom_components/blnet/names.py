"""Names for the inputs (S1..S16) and outputs (A1..A13) of the UVR, one per line."""

from __future__ import annotations

import re

from pyblnet_async import BLNETData

from .const import MAX_OUTPUT

_LINE = re.compile(r"^\s*([SA])\s*(\d{1,2})\s*[=:]\s*(.*?)\s*$", re.IGNORECASE)


def parse_names(text: str | None) -> dict[str, str]:
    """Parse lines like "S1 = Kollektor" or "A6: Heizkreis Pumpe".

    Empty lines and lines starting with # are ignored. Raises ValueError with the
    offending line for anything else.
    """
    names: dict[str, str] = {}
    for line in (text or "").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = _LINE.match(line)
        if not match or not match[3]:
            raise ValueError(line.strip())
        prefix, number = match[1].upper(), int(match[2])
        if not 1 <= number <= (16 if prefix == "S" else MAX_OUTPUT):
            raise ValueError(line.strip())
        names[f"{prefix}{number}"] = match[3]
    return names


def format_names(names: dict[str, str]) -> str:
    """Inverse of parse_names, inputs first, both in channel order."""
    keys = sorted(names, key=lambda k: (k[0] != "S", int(k[1:])))
    return "\n".join(f"{key} = {names[key]}" for key in keys)


def names_from_web(data: BLNETData) -> dict[str, str]:
    """The names the web interface shows, as a starting point for TA-only mode."""
    names = {f"S{n}": item.name for n, item in data.analog.items()}
    names.update({f"S{n}": item.name for n, item in data.digital_inputs.items()})
    names.update({f"A{n}": item.name for n, item in data.digital.items()})
    return names
