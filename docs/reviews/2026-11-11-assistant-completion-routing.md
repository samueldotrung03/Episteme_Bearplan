# Assistant completion routing for task titles containing Notes

**Pass with follow-ups.** On macOS arm64, reproduced the
user's request “Mark complete the review notes under draft seminar notes
complete in planner check” returning an update-task proposal that changed notes.
No Apply was sent during reproduction. The router selected update_task and
extracted trailing request text as notes; containment grounding accepted it.

Router v7 clarifies that action words in titles do not request field edits and
adds a completion example. Grounding drops editable fields from a contradictory
update-task route when the message begins with an explicit “Mark complete/done”
command. Such a misroute must clarify rather than propose a field edit. This
guard covers that explicit command pattern; it is not a general natural-language
intent validator. Existing Apply, revision, replay, Undo and domain rules remain.

- Affected tests: `.venv/bin/python -m pytest -q -p no:cacheprovider -p
  tests.connections_sandbox tests/test_assistant.py tests/test_assistant_actions.py
  tests/test_assistant_answers.py tests/test_assistant_carryover.py` — 85 passed
  in 2.28 seconds. Regressions cover the contradictory route without writes and
  valid completion plus Undo preserving the paused session and parent completion.
- Exact prompt with local qwen3:8b on disposable records returned complete_task
  targeting the correct subtask; every database table was unchanged by inference.
- The isolated demo was restarted with the fix, same disposable database and fake
  providers. No schema or frontend code changed.
- `.venv/bin/python tools/m5_evaluation.py --model qwen3:8b --output
  /tmp/bearplans-completion-routing-evaluation.json` — 30/30, routing 100%,
  zero unauthorized changes; gate passed. Temporary evidence may expire.
- Scoped diff whitespace check passed. Frontend checks were not rerun because
  no frontend files changed. The user confirmed the repaired proposal worked
  and reported the timer remained paused. That is the intended timer behavior;
  this report does not establish completion Apply/Undo.
