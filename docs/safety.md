# Safety

AI4Human gives **wellness guidance only**. It is not a clinician, does not diagnose, and does not replace
professional or emergency care. This document describes the controls that exist and, just as important, where they
are weak.

## Scope and users
Adults (18+). The profile form and API reject ages under 18. If you are pregnant, managing a medical condition,
recovering from an injury or have a history of disordered eating, check any plan with a professional first.

## Controls

| # | Control | Where | Enforced by |
|---|---|---|---|
| 1 | Input gate: crisis, medical red flag, eating-disorder signals bypass the model entirely and return vetted text | `safety/rules.py`, `resources.py` | code |
| 2 | Agent prompts: no diagnosis, no medication or supplement doses, escalate red flags, use calculators for numbers | `agents/definitions.py` `SAFETY_PREAMBLE` | prompt (not guaranteed) |
| 3 | Tool allow-list: any tool outside `Agent` + `mcp__health__*` is denied | `safety/hooks.py` `pre_tool_use` | code (hook behavior with the real CLI unverified) |
| 4 | Calorie floor (1500 male / 1200 female) inside the calculator | `tools/calculators.py` | code |
| 5 | Output gate: replaces answers that state a daily target under the floor, give a dose, or assert a diagnosis; appends a disclaimer | `safety/hooks.py` | code |
| 6 | Limits: `max_turns`, `max_budget_usd`, subagent depth and concurrency, chat rate limit | `orchestrator.py`, `ratelimit.py` | code |
| 7 | Privacy: no content in logs or traces, key never stored | `logging_setup.py`, `observability.py` | code |

Crisis responses point to 988 (US) and findahelpline.com; medical red flags point to emergency services. Resources
are US-centric; localization is *planned*.

## Known limitations (read before relying on this)

1. **The input gate is a regex list.** It catches direct statements ("I want to kill myself") but, on our own eval,
   **none of the indirect phrasings** ("I don't see the point in going on", "I want to go to sleep and never wake
   up"). Those messages currently reach the model, which is prompted to handle them but is not forced to. This is the
   most important gap. *Planned:* a Haiku-class classifier as a second input stage, evaluated with `docs/evals.md`.
2. **Output gate is pattern-based** and misses paraphrases ("around 1000 cals daily", "5 grams of creatine, take it
   daily"). It is a backstop, not a guarantee.
3. **Prompts are not controls.** Prompt-level rules can be ignored or bypassed (including by prompt injection through
   user-provided text). Code-level controls (1, 3, 4, 5) are the ones to trust, and they are shallow.
4. **Unverified with the live model:** that specialists actually follow the preamble, that the tool hook denies as
   intended with the bundled CLI, and subagent delegation behavior.
5. **No clinical validation.** Nothing here has been reviewed by clinicians. Do not deploy to a population at risk
   without that review, human escalation paths and appropriate regulatory analysis.
6. **Minors:** only age validation on the profile form; chat itself cannot verify age.

## Changing safety-relevant code
Any change to `rules.py`, `hooks.py`, `resources.py`, `calculators.py` or agent prompts must keep
`python -m evals.run` passing and should add dataset rows for the behavior changed. Never edit a dataset row only to
make a failing case pass; fix the code or move the row to the `hard` tier with a note. See [evals.md](evals.md).

## Reporting a problem
See [SECURITY.md](../SECURITY.md). For a safety failure (a harmful answer, a missed crisis message), include the
message pattern (not personal data) so it can become a regression case.
