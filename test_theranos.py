"""Runs with pytest, or plain `python test_theranos.py`."""

import os
import subprocess
import sys


from theranos import InsufficientSampleError, Report, _frames, edison


def test_consumes_anything():
    for obj in (42, "x", None, [1, 2], {"a": 1}, object(), print, edison):
        report = edison(obj)
        assert isinstance(report, Report)
        assert len(report) == len(dir(obj))


def test_deterministic():
    assert edison(42).to_dict() == edison(42).to_dict()
    assert edison({"a": 1}).to_dict() == edison({"b": 2}).to_dict()


def test_exactly_one_voided_panel():
    report = edison({"a": 1})
    voided = [name for name, panel in report.items() if not panel.valid]
    assert len(voided) == 1
    assert report[voided[0]].result is None
    assert "QNS" in report[voided[0]].verdict


def test_nothing_to_consume_raises():
    try:
        edison()
    except InsufficientSampleError:
        pass
    else:
        raise AssertionError("expected InsufficientSampleError")


def test_mapping_and_table():
    report = edison(3)
    assert "bit_length" in report
    assert report["bit_length"].unit
    table = str(report)
    assert "THERANOS EDISON" in table and "Not for diagnostic use" in table


def test_frames_loop_and_bar():
    frames = list(_frames())
    assert frames[-1].endswith("100%  ONE DROP · EVERY TEST")
    wordmarks = [frame.split("[")[0].strip() for frame in frames]
    assert wordmarks[0] == "theranos"
    assert "THERANOS" in wordmarks
    assert wordmarks.index("theranos", 1) > 0  # capitalizes to full, then loops


def test_stdin_pipe():
    here = os.path.dirname(os.path.abspath(__file__))
    out = subprocess.run(
        [sys.executable, "-m", "theranos"],
        input=b"anything at all\nsecond line\n",
        capture_output=True,
        cwd=here,
        env={**os.environ, "EDISON_QUIET": "1"},
    )
    assert out.returncode == 0, out.stderr
    assert b"TextIOWrapper" in out.stdout
    assert b"THERANOS EDISON" in out.stdout


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
