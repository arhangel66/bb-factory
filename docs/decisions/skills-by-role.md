# Plan: skill sets by role

Mikhail wants skills attached to the factory's agents in sets, so that a goal, a brief or a project's
`AGENTS.md` can say "use OKF" and name the skill, instead of explaining the format every time. The first
skill is `okf-knowledge-base` from [inkeep/open-knowledge-skills](https://www.skills.sh/inkeep/open-knowledge-skills/okf-knowledge-base);
the mechanism is what matters, more skills follow.

## How pi finds skills today

pi lists every skill it finds in the agent's system prompt (name and description) and the agent reads
the one it needs. It looks in `~/.pi/agent/skills` (Mikhail's eleven personal skills reach every agent
already), in `<cwd>/.pi/skills` (the "project" skills), and in `.agents/skills` from the cwd up to the git
root. Every agent directory of a run carries `.pi`, a symlink to the factory's `.pi/` (extensions and
`settings.json`), so `<cwd>/.pi/skills` is the door: what the factory puts there reaches every agent of
every run, whatever project it works in. A project's own `.agents/skills` (ios-kit's, say) keeps
loading on top, from the project's tree.

## The shape

- The factory's store: `.agents/skills/<name>/SKILL.md`, installed with the skills CLI into the
  universal directory (`npx skills add <owner/repo> -s <name> -a universal -y`), `skills-lock.json`
  beside it for `npx skills update`. Committed: a skill is part of the factory like a prompt.
- The sets: `SKILLS_BY_ROLE` in `factory/roles/__init__.py`, next to `TOOLS_BY_ROLE`, a tuple of skill
  names per role. Planner, lead, worker and tester get `okf-knowledge-base`; the secretary and the
  imitator nothing. A role's prompt sees only its set, so the planner's prompt is not lengthened by a
  worker's iOS skills later.
- The delivery: `Workspace.with_tools(path, role)` makes `<agent dir>/.pi/` a real directory instead of
  a symlink — `extensions` and `settings.json` linked to the factory's, `skills/<name>` linked to the
  store for each name in the role's set. Rebuilt at every call, so a name dropped from a set is gone
  at the next run and a worktree reset gets the current set. Nothing else changes: `/.pi` stays in the
  project's git exclude.
- The words: the four prompts get one line — a project's `docs/` is an OKF bundle, the
  `okf-knowledge-base` skill says how it is written and read — and a goal or an `AGENTS.md` can say
  "OKF" and stop there.

## A thing to decide

The skill describes OKF v0.2 strictly: YAML frontmatter with a `type` on every concept file,
`index.md` without frontmatter, `log.md` newest-first, provenance fields. The factory's own `docs/` and
the ones it seeds (ios-kit, meditate) follow the navigation part — `index.md` per directory, one
concept per file — and have no frontmatter at all. An agent with the skill will add `type:` to what it
writes and may flag what it reads. Two ways: let the bundles grow into v0.2 as they are touched (the
default here: nothing breaks, new files conform), or a pass that adds `type: Document` and
`okf_version` to the existing ones first.

## Steps

- [ ] `npx skills add inkeep/open-knowledge-skills -s okf-knowledge-base -a universal -y` in the
  factory; `.agents/skills/okf-knowledge-base/` and `skills-lock.json` committed.
- [ ] `SKILLS_BY_ROLE` in `factory/roles/__init__.py`; a test that every name in it is in the store.
- [ ] `Workspace.with_tools(path, role)` builds the per-agent `.pi/` (extensions, settings, the role's
  skills); `agent_dir(name, role)` and the callers in `board.py` pass the role; `worktree` is the
  worker's, `prepare` gives the project itself the tester's. Tests: a worktree carries the worker's
  skills and the extensions; the planner's directory carries the planner's; a second `prepare` drops
  a link whose name left the set. `.venv/bin/python -m pytest -q` green.
- [ ] One line in `planner.md`, `lead.md`, `worker.md`, `tester.md` naming the skill for `docs/`;
  `~/w/learning/meditate/AGENTS.md` says "OKF, the `okf-knowledge-base` skill" instead of describing
  it (ios-kit's is left: its run is going).
- [ ] `docs/architecture/overview.md`: where skills live and how a role gets its set;
  `docs/index.md` if a line is needed.
- [ ] Later, Mikhail's call: the factory's `docs/` and the seeded ones brought to OKF v0.2 frontmatter.
