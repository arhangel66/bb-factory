# Prompts

Everything a model reads lives in `factory/roles/prompts/`, nowhere else.

| file | who reads it | when |
|---|---|---|
| `planner.md` | planner thread | once, at spawn (`{goal}` filled by `factory/core/board.py`) |
| `lead.md` | lead thread, one per epic | once, at spawn, followed by the epic's brief |
| `secretary.md` | secretary thread, the only agent that talks to Mikhail | once, at spawn |
| `imitator.md` | imitator thread | once, at spawn |
| `worker.md` | worker thread, one per `code` task | once, at spawn, followed by the task's brief; ends with the ponytail ladder (after DietrichGebert/ponytail, MIT): YAGNI, reuse, stdlib, platform, one line, minimum |
| `tester.md` | tester thread, one per `test` task | once, at spawn, followed by the task's brief; holds the `bsk` recipes: phone captures, a synthetic drag through `evaluate` (braces doubled for `str.format`) |
| `task_brief.md` | imitator, worker, tester | every task sent to it, with the task's amendments appended |
| `conflict.md` | worker | when its branch does not merge: the conflict text and the main branch to merge in |
| `amended.md` | lead, worker, tester, imitator | when the planner or the lead amends the task it is at work on |
| `wake.md` | planner, lead, secretary | every wake: a handoff, a message, a review (`Board.review()`: open epics with age and sub-task counts, what went wrong since) or Mikhail's silence, plus their floor of the board |

Tool descriptions the models see are in `.pi/extensions/factory.ts`.
