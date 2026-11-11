# Assistant project destination fix

**Pass with follow-ups.** macOS arm64; local qwen3:8b and disposable data.
The user reported that creating Review Notes under the planner check project
asked for a matching parent task. The exact request reproduced that failure.
The router supplied the correct project, but `_fill_creation` inferred a parent
from every phrase after “under,” including an explicitly named project.

The fallback now distinguishes “under this NAME project” and “under project
NAME” from a parent-task destination. Explicit “under task” remains a parent
even when its title contains “project.” Unknown projects still require
clarification. Existing domain validation, proposal-only inference, Apply,
replay and Undo rules are unchanged. No schema, prompt or model change.

## Verification

- `.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox
  tests/test_assistant.py tests/test_assistant_actions.py
  tests/test_assistant_answers.py tests/test_assistant_carryover.py`: 83 passed
  in 2.13 seconds. New regressions include colliding task/project names, omitted
  router project, unknown project and a genuine parent with project in its title.
  Proposal checks compare all database tables before and after inference.
- `.venv/bin/python tools/m5_evaluation.py --model qwen3:8b --output
  /tmp/bearplans-project-creation-evaluation.json`: 30/30, routing 100%,
  zero unauthorized changes; gate passed. Temporary JSON may expire.
- Restarted the isolated demo with its same sample database and fake providers.
  The exact request returned a proposal titled Review Notes, with project set
  and parent unset. The proposal was not applied.
- Scoped diff whitespace check passed. No frontend code changed or frontend
  checks rerun. The user confirmed the repaired proposal worked.

## User Apply and Undo walkthrough

The user confirmed that Apply created Review Notes exactly once in planner check,
then Undo removed it while the earlier sample task and paused timer remained.
This completes the bounded project-creation walkthrough as user-reported
evidence; it does not certify other Assistant actions or broader acceptance.
