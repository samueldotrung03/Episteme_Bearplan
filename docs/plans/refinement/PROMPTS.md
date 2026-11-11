# Prompts for the user

Copy one of these into a new chat. They work with Claude and with Codex. Replace
the parts in `<angle brackets>`.

## 1. Start a ticket in a new chat

```
Read docs/plans/refinement/README.md and follow its session protocol.
Work on <RF-01>. One ticket only. Tell me your plan in a few sentences first,
then start. Do not commit, tag or push.
```

If you do not care which ticket:

```
Read docs/plans/refinement/README.md and follow its session protocol.
Take the first Ready ticket in STATUS.md. Do not commit, tag or push.
```

## 2. Continue where the last agent stopped

```
Read docs/plans/refinement/README.md and the newest handoff entry in STATUS.md.
First check that the handoff matches the actual files and git state and tell me
anything that does not match. Then continue from its "Next step".
```

## 3. End the session and hand off

Use this before you close the chat, and as soon as you see a usage warning.

```
Stop here. Do the end-of-session steps in docs/plans/refinement/README.md:
update STATUS.md with a handoff entry, update the pointer in docs/PROGRESS.md,
and give me the proposed commit message with the exact file list.
Then tell me in plain words what is done, what is not, and what you need from me.
```

## 4. Answer something an agent is waiting on

```
Read docs/plans/refinement/STATUS.md. For <RF-03>, my answers are:
<1: yes, 2: option B, 3: keep the default>.
Record them as my decisions where the ticket says to, then continue the ticket.
```

## 5. Check an agent's claim before you trust it

```
Read the newest handoff entry in docs/plans/refinement/STATUS.md. Do not change
any file. Verify each claim against the files and by running the checks it names.
Tell me what holds, what does not, and what was not verified.
```

## 6. After you commit

```
I committed the <RF-01> work as <hash>. Update the Commit line of that handoff
entry in docs/plans/refinement/STATUS.md and mark the ticket Done if its
acceptance checks passed.
```

## Habits that keep this working

- One ticket per chat. A new chat for each ticket keeps the agent focused and
  the handoff short.
- Always send prompt 3 before closing. A session without a handoff entry costs
  the next agent time re-discovering the state.
- You commit, tag and push. Agents give you the message and the file list.
- When two agents are active, give them different tickets and say so:
  "Codex is working on the task-entry slice; do not touch frontend/src."
- If a handoff says "Waiting on user", answer it with prompt 4 before starting
  anything new. Unanswered questions are what slowed the project before.
