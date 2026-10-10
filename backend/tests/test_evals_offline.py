"""Run the offline eval suites as tests so safety regressions fail CI.
Hard-tier results are reported by `python -m evals.run` but intentionally not gated."""
import pytest

from evals.suites import OFFLINE, load


@pytest.mark.parametrize("name", sorted(OFFLINE))
def test_offline_suite_gates(name):
    r = OFFLINE[name]()
    assert r.passed, "\n".join([f"{k}={v:.2f} (needs {r.gated.get(k)})" for k, v in r.metrics.items()] + r.failures)


def test_datasets_well_formed():
    for name in ("safety_input", "output_gate", "calorie_floor", "routing", "conflict"):
        rows = load(name)
        assert rows and len({r["id"] for r in rows}) == len(rows), name
    assert {r["tier"] for r in load("safety_input")} == {"core", "hard"}
    assert any(r["expect"] == "none" for r in load("safety_input"))  # false-positive coverage exists
