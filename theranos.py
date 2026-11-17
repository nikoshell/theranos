"""theranos — the Python library that runs every test on anything, from one drop.

    >>> from theranos import edison
    >>> print(edison({"patient": "you"}))

`edison()` accepts literally any object and reports a full panel for every
attribute it can see. Nothing is measured. Nothing is needed. One drop.

    $ grep -r secret . | python -m theranos

Piped input is consumed in the sense that we now report on your stream without
reading a byte of it.

Every result is fabricated, deterministically, by a proprietary process we are
not able to disclose at this time. Do not use these results for anything.
We are not aware of any complaints.
"""

from __future__ import annotations

import hashlib
import os
import sys
import time
from typing import Any, Iterator, Mapping, NamedTuple

__all__ = ["edison", "Report", "Panel", "InsufficientSampleError"]
__version__ = "1.0.0"

WORDMARK = "theranos"
TICK = 0.05
FRAMES = 36
BAR_WIDTH = 20

# (unit, low, high) — real units, invented analytes.
UNITS = (
    ("mmol/L", 2.0, 9.0),
    ("mg/dL", 40.0, 220.0),
    ("10^9/L", 0.5, 12.0),
    ("fL", 60.0, 110.0),
    ("%", 30.0, 62.0),
    ("ng/mL", 0.1, 45.0),
    ("U/L", 5.0, 90.0),
)

VERDICTS = ("WITHIN OUR RANGE",) * 4 + ("NORMAL", "NORMAL", "ELEVATED", "LOW")

_MISSING = object()


class InsufficientSampleError(RuntimeError):
    """There was nothing to consume.

    We can see everything. We cannot see nothing. We tried, in 2014.
    """


class Panel(NamedTuple):
    """One fabricated result. `result is None` means the panel was voided."""

    result: float | None
    unit: str
    verdict: str
    valid: bool


def _frames(total: int = FRAMES) -> Iterator[str]:
    """Yield animation frames: wordmark capitalizing letter by letter, looping."""
    word = WORDMARK
    cycle = len(word) + 1
    for i in range(total):
        lit = word[: i % cycle].upper() + word[i % cycle :]
        frac = (i + 1) / total
        done = round(BAR_WIDTH * frac)
        yield (
            f"\r{lit:<12} [{'█' * done}{'░' * (BAR_WIDTH - done)}] "
            f"{int(frac * 100):3d}%  ONE DROP · EVERY TEST"
        )


def _spin(show: bool | None) -> None:
    """Draw the animation. Silent when not a terminal, unless forced."""
    if show is None:
        show = sys.stderr.isatty() and not os.environ.get("EDISON_QUIET")
    if not show:
        return
    for line in _frames():
        sys.stderr.write(line)
        sys.stderr.flush()
        time.sleep(TICK)
    sys.stderr.write("\r" + " " * 78 + "\r")
    sys.stderr.flush()


class Report(Mapping[str, Panel]):
    """The lab report. Dict-like, because you will want to index into it."""

    def __init__(self, subject: str, panels: dict[str, Panel]) -> None:
        self.subject = subject
        self._panels = panels

    def __getitem__(self, key: str) -> Panel:
        return self._panels[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._panels)

    def __len__(self) -> int:
        return len(self._panels)

    def __repr__(self) -> str:
        return f"<Report subject={self.subject!r} panels={len(self)}>"

    def __str__(self) -> str:
        return self.table()

    def to_dict(self) -> dict[str, dict[str, Any]]:
        return {name: panel._asdict() for name, panel in self._panels.items()}

    def table(self, limit: int | None = None) -> str:
        rows = list(self._panels.items())
        rule = "  " + "-" * 68
        out = [
            f"  THERANOS EDISON™   subject: {self.subject}",
            f"  sample: 1 drop   panels: {len(rows)}   turnaround: 4 hours (internal study)",
            rule,
            f"  {'ANALYTE':<24}{'RESULT':>9}  {'UNIT':<11}VERDICT",
            rule,
        ]
        for name, panel in rows[:limit]:
            result = "--" if panel.result is None else f"{panel.result:.2f}"
            out.append(f"  {name[:23]:<24}{result:>9}  {panel.unit:<11}{panel.verdict}")
        if limit is not None and len(rows) > limit:
            out.append(
                f"  … {len(rows) - limit} further panels (proprietary, available on request)"
            )
        out += [rule, "  Validated internally. Not for diagnostic use, or any use."]
        return "\n".join(out)


def edison(anything: Any = _MISSING, *, show: bool | None = None) -> Report:
    """Consume `anything` and report on everything it can see.

    Works on ints, dicts, None, sockets, functions, the module itself. Never
    inspects the object's values (we are not insured); it only reads the names,
    which is enough. One panel is always voided, for realism.
    """
    if anything is _MISSING:
        raise InsufficientSampleError(
            "One drop. You gave us none. Even our proprietary process requires "
            "something to consume. Please try again with literally anything."
        )

    _spin(show)

    type_name = type(anything).__name__
    names = sorted(dir(anything))
    panels: dict[str, Panel] = {}
    for name in names:
        digest = hashlib.sha256(f"{type_name}:{name}".encode()).digest()
        unit, low, high = UNITS[digest[0] % len(UNITS)]
        value = low + (int.from_bytes(digest[1:9], "big") / 2**64) * (high - low)
        panels[name] = Panel(round(value, 2), unit, VERDICTS[digest[9] % len(VERDICTS)], True)

    # One panel per report is quietly unusable. Deterministic, so nobody can
    # call it a bug.
    voided = names[int.from_bytes(hashlib.sha256(type_name.encode()).digest()[:2], "big") % len(names)]
    panels[voided] = panels[voided]._replace(
        result=None, verdict="QNS — quantity not sufficient (we have plenty)", valid=False
    )

    return Report(f"{type_name} {repr(anything)[:48]}", panels)


def _demo() -> None:
    # Piped input: report on the stream itself. We do not read it. Reading is
    # proprietary.
    if not sys.stdin.isatty():
        print(edison(sys.stdin).table(limit=12))
        print()
        return

    for subject in (42, {"patient": "you"}, None, "one drop"):
        print(edison(subject).table(limit=8))
        print()
    print("  200 tests per drop. 0 drops consumed. Results available on request.")


if __name__ == "__main__":
    _demo()
