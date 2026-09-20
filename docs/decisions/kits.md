# Plan: kits — a preset named in the run

Mikhail's ask: no hand seeding before a run. A run says `kit=IOS` and the project gets the kit's skills,
its instructions and its experience by itself; the goal talks about the product only. The first kit is
ios-kit, the repository the factory built for itself on 2026-09-20; more come the same way (a web kit,
a bot kit).

## What a kit is

A kit is a repository with three things the factory knows how to hand to a project: `.agents/skills/`
(the skills that proved themselves there), `docs/index.md` (the way in: quickstart, tools, verdicts) and
a brief — the paragraph every run on that kit is told. The factory does not know what iOS is; it knows
where the kit's skills, docs and brief are.

```python
# factory/kits.py
@dataclass(frozen=True)
class Kit:
    name: str    # "ios"
    root: Path   # where it lives; its .agents/skills and docs/index.md are read from here
    brief: str   # prepended to every goal run on it: what to read first, how to build, what to fix where

IOS = Kit("ios", Path.home() / "w/learning/ios-kit", brief="""\
This project is built with the ios kit at {root}: read its `docs/index.md` first (a quickstart in three
commands), make the app with its starter, build, run, test and drive it the way its docs say; its
skills are in this project's `.agents/skills/`. What the kit lacks is fixed in the kit — a task that
works in {root} and commits there — never worked around here; the report says what the kit gained.
Agents run in parallel on one Mac: every agent boots a simulator device of its own (`xcrun simctl
create`, deleted when done), never a shared one, and keeps derived data in its own tree.
""")
```

## What happens at the start of a run

`run(goal, config, workdir, slots, kit=IOS)`:

1. `Workspace.prepare(kit)` seeds the project before any thread exists, and commits what it seeded:
   - `.agents/skills/<name>/` copied from the kit for every skill the project does not have yet
     (a project may have rewritten one: its copy wins), `.claude/skills -> .agents/skills` so
     Mikhail's Claude Code sees the same; `skills-lock.json` copied when absent.
   - `AGENTS.md`: a `## Kit` section appended when there is none — the kit's name, where it lives,
     that its `docs/index.md` is the way in, that its skills are in `.agents/skills/`. The rest of
     `AGENTS.md` (docs in OKF, the check) is the project's own, written once by whoever makes it.
   - One commit, `seeded with the ios kit`, force-added: Mikhail's global gitignore hides
     `AGENTS.md` and `.claude/`.
   Every worktree branches from that commit, so the first worker already has the skills — the gap of
   the ios-kit run (a skill reaches a worker only once merged into its branch) is closed.
2. The goal the planner gets is `kit.brief` and then the goal text: the planner reads the way in
   before the product. `run.json` records the kit's name.
3. `resume()` needs nothing: the project is seeded already.

Not in the kit: the models, the slots, the tester's tools. Those stay in `construct.py` where they are.

## What changes in the meditate goal

Its first paragraph ("Use ios-kit at … for everything …") and its last sentence about simulators move
into `IOS.brief`; the goal keeps the product: the content, the design gate, the six items, the stack.

## Relation to other plans

- [skills-by-role](skills-by-role.md) is the factory's own layer (OKF for every role, whatever the
  project); a kit is the project's layer (iOS for this project). pi sees both.
- [green-handoff](green-handoff.md) wanted the factory to seed `AGENTS.md` and `docs/` into a project
  it creates; step 1 here is that seeding, for the kit's part. The generic part (docs skeleton, the
  check gate) stays open there.

## Steps

- [x] `factory/kits.py`: `Kit`, `IOS`.
- [x] `Workspace.prepare(kit: Kit | None)` seeds as above; `seed(kit)` as its own method. Tests: a
  fake kit directory with two skills → the project has both, `AGENTS.md` has the section, one commit;
  a second prepare adds nothing; a project's own copy of a skill is kept.
- [x] `Board.run(goal, kit)`: the brief before the goal, the kit's name in `run.json`;
  `construct.run(..., kit)`. Tests: the planner's prompt starts with the brief.
- [x] `construct.py`: `meditate` shortened, `run(meditate, power_real, …, slots=10, kit=IOS)`.
- [x] `docs/architecture/overview.md`: kits; `~/w/learning/meditate/AGENTS.md` loses the hand-written
  kit paragraph (the seed writes it).
- [x] Launched: the meditation run of 2026-09-20 12:40 named `kit=IOS` and the seeding did the rest —
  `seeded with the ios kit` (1bbbc77) copied the kit's nine skills into `.agents/skills/`, linked
  `.claude/skills` and appended the `## Kit` section to `AGENTS.md`, before the planner existed. Whether
  the first worker uses the starter without being told twice is what the run itself shows.
