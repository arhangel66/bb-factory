# Agents

## Project knowledge

Project knowledge is stored in `docs/` using the
[Open Knowledge Format](https://github.com/inkeep/open-knowledge-skills) (OKF).

- Start from `docs/index.md` when project context is needed, and navigate through directory `index.md`
  files progressively. Open only the documents the current task needs.
- Treat code as the source of current behaviour, and `docs/` as the source of product intent,
  architectural rationale, constraints and previous decisions.
- Keep `docs/` current as part of the work, not after it: a new part gets its document and its line in the
  index, and a document a change makes wrong is fixed in the same change.

## How the code is written

By a lazy senior developer — the ponytail ladder, after
[DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) (MIT). Lazy means efficient, not
careless: the best code is the code never written. Before writing any, stop at the first rung that holds —
is it needed at all, is it already in this codebase, does the standard library do it, does the platform
cover it, does an installed dependency solve it, can it be one line — and only then write the minimum that
works.

No abstraction nobody asked for, no configurability for a value that never changes, no scaffolding "for
later". Deletion over addition, boring over clever, the fewest files possible. Not lazy about:
understanding the problem, validation at trust boundaries, error handling that prevents data loss,
security, accessibility, and anything the task asks for.

## Commits

Every finished step is a commit: the check below is green before it, the message is one short line in
english saying what changed. No work is left uncommitted when a task is handed off.

## Check

The first task writes the check here — the one command that builds and tests this project — and it stays
green from then on.

```
```
