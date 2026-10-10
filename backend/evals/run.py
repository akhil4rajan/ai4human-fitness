"""Run evals:  python -m evals.run [--suite offline|live|NAME ...] [--json out.json]

offline (default): deterministic, no key, gates CI.  live: needs ANTHROPIC_API_KEY, costs money."""
import argparse
import json
import os
import sys

from evals.suites import LIVE, OFFLINE, SuiteResult


def render(r: SuiteResult) -> str:
    status = "PASS" if r.passed else "FAIL"
    lines = [f"[{status}] {r.name}"]
    for k, v in sorted(r.metrics.items()):
        gate = r.gated.get(k)
        mark = "" if gate is None else f"  (gate >= {gate:.2f}{' ok' if v >= gate else ' FAILED'})"
        lines.append(f"    {k:<34}{v:6.1%}{mark}")
    lines += [f"    ! {f}" for f in r.failures]
    lines += [f"    note: {n}" for n in r.notes]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--suite", nargs="*", default=["offline"], help="offline | live | suite names")
    ap.add_argument("--json", help="write results to this file")
    args = ap.parse_args(argv)

    names: list[str] = []
    for s in args.suite:
        names += list(OFFLINE) if s == "offline" else list(LIVE) if s == "live" else [s]

    key = os.environ.get("ANTHROPIC_API_KEY", "")
    results: list[SuiteResult] = []
    for n in names:
        if n in OFFLINE:
            results.append(OFFLINE[n]())
        elif n in LIVE:
            if not key:
                print(f"skip {n}: set ANTHROPIC_API_KEY (live suites call the model and cost money)")
                continue
            results.append(LIVE[n](key))
        else:
            print(f"unknown suite {n!r}; choose from {sorted([*OFFLINE, *LIVE])}")
            return 2

    for r in results:
        print(render(r))
    if args.json:
        with open(args.json, "w") as f:
            json.dump([{"suite": r.name, "passed": r.passed, "metrics": r.metrics, "failures": r.failures}
                       for r in results], f, indent=2)
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
