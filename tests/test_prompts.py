from factory.roles import PROMPTS, prompt

FIELDS = {"goal": "a goal", "event": "an event", "board": "a board", "key": "FAB-1", "title": "a task", "type": "code",
          "priority": "high", "description": "do it", "conflict": "CONFLICT", "main": "master", "who": "planner",
          "text": "a change"}


def test_every_prompt_renders() -> None:
    # a brace in a prompt (a code sample) breaks str.format at the spawn, never before
    for file in PROMPTS.glob("*.md"):
        rendered = prompt(file.stem, **FIELDS)

        assert "{{" not in rendered and "}}" not in rendered, file.name
