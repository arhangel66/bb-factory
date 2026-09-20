# Diagrams

The diagrams that say what is true today are in [../overview.md](../overview.md), in the text they
explain: the topology at the top, one run as a sequence below it. They are Mermaid, so they render
wherever the markdown does, and they are changed in the same commit as the thing they describe.

- [factory.html](factory.html) — three hand-drawn boards: the imitator test loop, the full topology and
  a run as a sequence. Open it in a browser; it is a designed page, not markdown.

  **It describes an earlier factory.** It was last touched by `a006ab8`, the commit that folded the
  orchestrator into the board, and it still draws `factory/orchestrator.py` as a loop beside a separate
  store. There is no orchestrator now, the board owns the tasks, and the page knows nothing of worktrees,
  kits, costs or the wait for Mikhail's answer. Read it as a picture of where the factory came from.
