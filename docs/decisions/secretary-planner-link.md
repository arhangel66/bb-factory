# Plan: the secretary can ask the planner and come back

Mikhail noticed on 2026-09-20 that when he asks the secretary how the work is going, the secretary
answers from what it sees itself instead of asking the planner and coming back with the planner's
answer. That is what the tools allow: `tell_planner` is one-way, the planner has no tool to answer the
secretary, and the only message a planner sends the secretary is `report`, which the board takes as the
end of the goal (`Board.reported()` matches any planner → secretary message). The secretary's prompt says
"answer him yourself" and the planner's prompt says Mikhail is reachable only through an `ask` task; so
a question about the state of the work is answered from the board lines in the secretary's wake, which
say which tasks are open, not what is going on.

## The shape

```
Mikhail --"how far is it?"--> secretary --tell_planner--> planner --tell_secretary--> secretary --contact_human--> Mikhail
```

- `tell_secretary(text)`, planner only: a message planner → secretary with no status. `report` keeps its
  status (`green`/`yellow`/`red`) and stays the only message that ends the goal: `reported()` looks at
  the status, not at the pair of names.
- `tell_planner` is also for his question the secretary cannot answer from the handoffs it has seen;
  the planner's answer wakes the secretary like anything else in `messages.jsonl`.
- The secretary's prompt: a question about the work — how far, what is being done, whether a thing is
  finished — goes to the planner; the secretary tells Mikhail it is asking and retells the answer when
  it comes. The board lines in its wake are for the secretary's own orientation, not for his answer.
- The planner's prompt: a message from the secretary is either Mikhail's word (tasks, amendments) or
  his question (`tell_secretary`, at once, short, no task).

The threads of the ios-kit run of 06:31 loaded the extension before this tool existed: the fix reaches
the next run (Meditate), not the one going.

## Steps

- [x] `write_message(sender, to, text, status=None)`; `Board.reported()` requires a status. Test: a
  planner → secretary message without a status wakes the secretary and does not end the run.
- [x] `tell_secretary` in `.pi/extensions/factory.ts`, in the planner's `TOOLS_BY_ROLE`; `tell_planner`'s
  description names the question.
- [x] `secretary.md` and `planner.md` as above.
- [x] `docs/architecture/overview.md`: the tool in the list. Index line here.
