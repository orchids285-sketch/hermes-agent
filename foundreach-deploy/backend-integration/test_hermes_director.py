"""Unit tests for hermes_director — deterministic (mocked HTTP), no live Hermes needed.

Run:  python -m pytest ultimate_agent/core/test_hermes_director.py -q
   or: python ultimate_agent/core/test_hermes_director.py   (built-in runner below)

Covers the safety-critical contracts:
  * disabled (env unset) => every hook is a no-op with safe defaults
  * quality_gate: accept high score, reject low (+ redo_tasks), honor the redo cap
  * graceful degradation: Hermes down (HTTP error) => fail-open (accept / "" / True), never raises
"""
import importlib.util
import json
import os
from unittest import mock

_HERE = os.path.dirname(__file__)
_PATH = os.path.join(_HERE, "hermes_director.py")


def _load(env):
    """Load a FRESH hermes_director with the given env (module reads env at import)."""
    with mock.patch.dict(os.environ, env, clear=True):
        spec = importlib.util.spec_from_file_location("hd_under_test", _PATH)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
    return m


def _fake_resp(payload: dict):
    """urlopen() stand-in: the code does json.load(urlopen(...)), i.e. it calls .read()
    on the RETURN value directly (not a context manager)."""
    body = json.dumps({"choices": [{"message": {"content": json.dumps(payload)}}]}).encode()
    resp = mock.MagicMock()
    resp.read.return_value = body
    return resp


ON = {"HERMES_API_URL": "https://h/v1", "HERMES_API_KEY": "k", "HERMES_QUALITY_BAR": "7", "HERMES_MAX_REDOS": "2"}


def test_disabled_is_noop():
    hd = _load({})  # nothing set
    assert hd.enabled() is False
    assert hd.quality_gate([{"output": "x"}], [], 0)["accept"] is True
    assert hd.strategize("obj", []) == ""
    assert hd.should_continue({"iteration": 1}) is True
    hd.learn("o", [], [], True, 5.0)  # must not raise


def test_quality_gate_accepts_high():
    hd = _load(ON)
    with mock.patch("urllib.request.urlopen", return_value=_fake_resp(
            {"score": 9, "accept": True, "reason": "great", "redo_tasks": []})):
        g = hd.quality_gate([{"output": "strong"}], [{"verdict": "ok"}], 0)
    assert g["accept"] is True and g["score"] == 9.0


def test_quality_gate_rejects_low_with_redo():
    hd = _load(ON)
    with mock.patch("urllib.request.urlopen", return_value=_fake_resp(
            {"score": 3, "accept": False, "reason": "weak",
             "redo_tasks": [{"role": "researcher", "instruction": "add named companies"}]})):
        g = hd.quality_gate([{"output": "weak"}], [{"verdict": "vague"}], 0)
    assert g["accept"] is False and g["score"] == 3.0 and g["redo_tasks"]


def test_quality_gate_honors_redo_cap():
    hd = _load(ON)  # MAX_REDOS=2
    # at/over the cap it must accept WITHOUT even calling Hermes (fail-safe termination)
    with mock.patch("urllib.request.urlopen", side_effect=AssertionError("should not be called")):
        g = hd.quality_gate([{"output": "still weak"}], [], redo_count=2)
    assert g["accept"] is True and "cap" in g["reason"]


def test_graceful_when_hermes_down():
    hd = _load(ON)
    with mock.patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
        assert hd.quality_gate([{"output": "x"}], [], 0)["accept"] is True   # fail-open
        assert hd.strategize("obj", []) == ""
        assert hd.should_continue({"iteration": 1}) is True
        hd.learn("o", [], [], False, None)  # must not raise


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        try:
            fn(); passed += 1; print("PASS", fn.__name__)
        except Exception as e:  # noqa: BLE001
            print("FAIL", fn.__name__, "->", repr(e))
    print(f"\n{passed}/{len(fns)} passed")
