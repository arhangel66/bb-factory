"""`bb notify`: the board's own voice. A run that is in trouble is the one thing no agent can report."""

import subprocess

SOURCE = "factory-board"


def notify(route: str, title: str, body: str, action: str, dedupe_key: str) -> None:
    # said from inside an error handler, so it never raises: a board that cannot complain still runs
    try:
        subprocess.run(["bb", "notify", "--source", SOURCE, "--kind", "agent", "--route", route,
                        "--title", title, "--body", body, "--action", action, "--dedupe-key", dedupe_key],
                       capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        pass
