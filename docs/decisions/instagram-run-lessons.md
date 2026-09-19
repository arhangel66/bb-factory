# Lessons of the Instagram run

The first big real run (2026-09-19, 20:26–21:36, 30 tasks, all green) built the MVP but showed how the
factory wastes its slots and its handoffs. Fixes, in order of what they cost the run.

## Seen

- Ten slots, one thread: the planner chained the epics through their tests, the first lead chained its
  code tasks the same way. The prompts said "create tasks in order", the models read "in a chain".
- Four polish tasks in parallel, three conflicted on `base.html`. The board marked them `done` anyway,
  spawned three redo copies in parallel on the same files, and the lead's test started with one change of
  four in the project. Nobody told the lead.
- The tester's brief said "confirm the epic requirements"; the tester sees only its task text.
- On a green handoff the planner and the leads did nothing: the prompt said so. Workers' "follow-ups" were
  boilerplate ("replace the secret before production"); the planner saw only the lead's one-line retelling.
- The planner never asked Mikhail anything, although the goal asked for one `ask` before the epics.
- Two tests of every area: the lead's and the planner's.
- The tester passed pages Mikhail calls ugly: it checked "no overflow" by metrics, not the look against the
  real thing; it burned a hundred steps finding a browser recipe.
- The secretary invented agreement ("yes, we agreed", "the tester did check it in a browser").
- The run ended with the report and archived the planner and the secretary; Mikhail wanted to keep talking.

## Plan

- [x] Prompts: block only on real dependencies, parallel by default; a task is self-contained; the next
      task is created after the handoff it builds on; one `ask` before the epics; the lead tests its own
      epic, the planner tests the whole; look is compared with the real thing, screens named
- [x] Handoffs teach: worker and tester hand off in parts — done, noticed, left (tester: checked, failed,
      noticed); the lead and the planner read "noticed" and decide per point; the lead's epic handoff
      carries what it skipped; the lead is the team lead of its epic's quality
- [x] Tester: look with its eyes in a person's viewport, screenshots in the handoff, a five-command `bsk`
      recipe, say what could not be checked, a "noticed" list for a person and for an agent
- [x] Secretary: retell as it is, never claim on the team's behalf
- [x] Brief: the executor gets its epic's description and the handoffs of the tasks it waited on
      (`Board.brief`)
- [x] Conflict: the original task is canceled (its work is not in the project), whatever waited on it waits
      on the copy, the copy waits on the code tasks in flight; the timeline shows the original grey
- [x] Review instead of heartbeat: the planner is asked every 15 minutes, regardless of activity, to look
      at the goal against what was handed off
- [x] Linger: after the report the planner and the secretary stay; Mikhail's messages keep arriving until
      Ctrl-C. `Board.resume()` re-attaches a board to the run `state/current` points at, unarchiving both
- [x] The planner and the leads read the project's `docs/` (`read`, `ls`; the prompt says where and that
      the code stays unread)
- [ ] Files on a handoff (Mikhail): `handoff` takes `files`, the board copies them into the run
      (`state/runs/<run>/files/<key>/`) — the tester's screenshots, a worker's log — the wake names them,
      the task's details in the timeline show images inline and the rest as links
- [ ] Notes for the long-lived agents (planner, lead, secretary): a journal that survives a compaction of
      their thread, re-read on every wake; notes about the project belong in the project's `docs/`
- [ ] A researcher role: web search and deep research, asked by the planner and the leads for best
      practices, answers as a handoff; it also searches [skills.sh](https://www.skills.sh/) for a skill that
      already knows the subject
- [ ] The rest is [green-handoff.md](green-handoff.md): the worker merges master in and runs the check
      before it hands off, projects start with `AGENTS.md` and `docs/`
