import json
from pathlib import Path

from factory.core.board import Board
from factory.core.tracker import Tracker
from factory.core.workspace import Workspace
from factory.kits import IOS, Kit
from factory.roles import AgentConfig, Config, Model, Role, Thinking
from factory.state import RUN_FILE
from factory.tools.bb import Threads
from factory.tools.telegram import Telegram
from factory.tools.voice import Voice

# who runs on what: every agent names its model and how long it thinks, nothing is left to a default
PLANNER = AgentConfig(prompt=Role.planner)
LEAD = AgentConfig(prompt=Role.lead)

# test run: one imitator plays every worker and tester, one thread so its story stays consistent;
# the planner and the leads are real, they only create tasks
IMITATOR = AgentConfig(prompt=Role.imitator, model=Model.gpt_5_6_terra, thinking=Thinking.low, mode="shared")

# real run: a fresh thread per task, each worker in a git worktree of the project
WORKER = AgentConfig(prompt=Role.worker, model=Model.gpt_5_6_luna, thinking=Thinking.high)
TESTER = AgentConfig(prompt=Role.tester)
# one thread for the whole run: it is one person
SECRETARY = AgentConfig(prompt=Role.secretary, mode="shared")

# power run: the strongest planner, strong leads, a cheap tester that only drives and looks
PLANNER_POWER = AgentConfig(prompt=Role.planner, model=Model.gpt_6_astra, thinking=Thinking.high)
LEAD_POWER = AgentConfig(prompt=Role.lead, model=Model.gpt_5_6_sol, thinking=Thinking.high)
TESTER_POWER = AgentConfig(prompt=Role.tester, model=Model.kimi_k3, thinking=Thinking.medium)


def run(goal: str, config: Config, workdir: Path, slots: int, kit: Kit | None = None) -> None:
    # linger: after the report the planner and the secretary stay, Mikhail talks to the run in Telegram until Ctrl-C;
    # kit: the project is seeded with its skills and the planner hears its brief before the goal
    Board(config, tracker=Tracker(), threads=Threads(), workspace=Workspace(workdir), telegram=Telegram(voice=Voice()),
          slots=slots, linger=True).run(goal, kit)


def resume(config: Config, slots: int) -> None:
    # the run state/current points at, after its board has ended: Mikhail goes on talking to it in Telegram
    workdir = Path(json.loads(RUN_FILE.read_text())["workdir"])
    Board(config, tracker=Tracker(), threads=Threads(), workspace=Workspace(workdir), telegram=Telegram(voice=Voice()),
          slots=slots).resume()


if __name__ == "__main__":
    test_config: Config = {
        Role.planner: PLANNER,
        Role.lead: LEAD,
        Role.worker: IMITATOR,
        Role.tester: IMITATOR,
        Role.secretary: IMITATOR,  # a test run reaches nobody's Telegram
    }
    real_config: Config = {
        Role.planner: PLANNER,
        Role.lead: LEAD,
        Role.worker: WORKER,
        Role.tester: TESTER,
        Role.secretary: SECRETARY,
    }
    power_real: Config = {
        Role.planner: PLANNER_POWER,
        Role.lead: LEAD_POWER,
        Role.worker: WORKER,
        Role.tester: TESTER_POWER,
        Role.secretary: SECRETARY,
    }

    task = """\
Prepare "ios-kit": a kit for building iOS apps on this Mac fast, from the idea to a running, tested app, for
the agents of this factory and for Mikhail with Claude Code. The kit is this repository: `docs/` with what is
known, `.agents/skills/` with the skills that proved themselves, and a starter that makes a new app. Report
by 13:00 today; an honest partial report beats a late one.

This is research as much as building: for every part of the kit there are several ways, and the kit keeps
the one that won on this Mac, with the others and their numbers written down so nobody tries them twice.
Try at least two ways for each of these, on the same small app, measured, before choosing: making the
project without the Xcode GUI (XcodeGen, Tuist, a Swift package with an app target, a `.pbxproj` written
once and copied); building and running (xcodebuild flags, derived data placement, warm versus cold
simulator, `xcodebuild` versus `swift build` where it applies); readable test output (xcbeautify,
xcpretty, raw); driving the app (`axe`, `idb`, `maestro`, XCUITest itself, `simctl` alone); skills
(from skills.sh, from Mikhail's own projects, written here). Every verdict is a line in `docs/` with the
measurement behind it.

Start with `docs/prior-art.md`: Mikhail's own iOS projects on this Mac, with build and run scripts, an
XCUITest layer, three skills already installed, and a widget install workaround. Read them, take what
works, and judge their skills like any other candidate.

The Mac: MacBook Pro M2 Max, macOS 26, Xcode 26.6 at /Applications/Xcode.app (Swift 6.3), iOS 26.2 and 26.4
simulator runtimes with iPhone devices, Homebrew, Node and npx, `axe` (simulator UI automation: describe-ui,
tap, type, swipe, button, screenshots through stream-video), `ios-deploy`. Nothing else for iOS. No `sudo`,
no Apple ID, no App Store, no physical device, no paid service: what needs one is a line for Mikhail in the
report. Everything else may be installed with brew or npm; what is installed is written down in `docs/` with
the version and the reason, and what was installed and rejected is uninstalled.

What the kit must do, proven not described:
1. Start: one command (`./new-app.sh <Name>` or the like) makes a new SwiftUI app in a directory without the
   Xcode GUI: the project, a unit test target, a UI test target, a `check.sh` that builds and runs both, and a
   `run.sh` that builds, installs and launches it on a simulator. Under 3 minutes from nothing to the app on
   screen, unattended.
2. Loop: change one line, see it on the simulator — the fastest way found on this Mac, measured in seconds and
   written down with what made it fast (a warm simulator, incremental builds, derived data, flags) and what
   was tried and was slower.
3. Test: unit tests and XCUITest run from the shell with readable output (a failure names the test and the
   line); a screenshot of any screen from the shell; the app driven from the shell — taps, typing, reading
   the screen — with the tool that won; the recipes in a skill, each one tried.
4. Skills: search skills.sh (`npx skills find <words>` searches, `npx skills add <owner/repo>` installs; the
   `find-skills` skill in vercel-labs/skills says how) for iOS, SwiftUI, Swift testing, Xcode and simulator
   skills, and take the three from VoicePen and the `ios` skill from GymBuddy; install the candidates into
   `.agents/skills/`; use each in real work of this run and keep it only if it made the work better; rewrite
   what is nearly right; every reject is a line in `docs/` with the reason. Write skills of the kit's own
   for what nobody had: this Mac's loop, the starter, driving the simulator.
5. Proof: build one small real app with the kit — "Ledger": a list of expenses, add and edit on a second
   screen, a total, persisted across a relaunch; unit tests of the total, a UI test of add; a tester drives it
   on the simulator and takes screenshots. Built with the kit and nothing else: what the kit lacked is fixed
   in the kit, not worked around in the app.
6. Knowledge: `docs/` in OKF holds it all — the Mac, the tools and versions, every comparison with its
   numbers and verdict, the skills kept and rejected with why, how to start the next app in three lines.
   `./check.sh` in AGENTS.md is the kit's check: the first task writes it and it stays green.

How to run it: first a foundation task that maps the Mac and makes one starter work once, whichever way is
quickest to get going; then in parallel the comparisons — project generation, the loop, test output,
driving the app, skills — each an epic or a task in its own files, each ending in a verdict in `docs/` and
the winner in the kit; then Ledger with the kit; last, a test task that clones the kit fresh into a new
directory, follows `docs/` only, and gets to a running, tested new app. The tester in this run has no
browser and no `bsk`: a shell, `xcrun simctl`, `axe` and what the kit documents. Write test tasks in those
terms, and every check names its evidence: a screenshot path, a command and its output. Agents run in
parallel on one Mac: every agent boots a simulator device of its own (`xcrun simctl create`, deleted when it
is done), never a shared one, and keeps derived data in its own tree. Mikhail is reachable through the
secretary but slow to answer: decide yourself where you can.
"""
    # the run after ios-kit reports: the first app built with the kit
    meditate = """\
Build "Meditate": an iOS app for Mikhail's iPhone that plays his guided meditations. Report by 20:00 today;
an honest partial report beats a late one.

Input: `content/` holds the meditations as mp3 files, one meditation per file — one today,
`meditation_small.mp3`, 92 minutes, no tags; more will come. The look to match is in `docs/reference/`:
Practico, two screens, described there. The audio is Russian; the app speaks Russian, the code and the
docs English.

Design first, code after: before any app code, three design variants of the app — for each, the list screen
and the player as images generated the way item 2 says, one look per variant (colors, ring, glyph style,
typography), each a real answer to the Practico reference, not three shades of one. The secretary sends
the three to Mikhail as files with one line each and asks which he likes; the coding tasks wait for his
choice, and go on with the variant he named, with his remarks. If he is silent for two hours, the
planner picks and says so in the report.

Product:
1. Catalog: every mp3 in `content/` is a meditation with a title, a one-line description, a duration and an
   icon. The title and the description come from the audio itself: transcribe its first minutes locally
   and name it as a person would — a file name is never a title. Local transcription is already on this
   Mac, read-only: Mikhail's app Beseda at /Users/mikhail/w/learning/beseda does it through transcribe.cpp
   (handy-computer/transcribe.cpp; the Swift wrapper is `Vendor/TranscribeCpp`, the xcframework is in
   `Package.swift`, the models it downloaded are in `~/Library/Application Support/Beseda/runtime/models/`:
   `gigaam-v3-e2e-rnnt-Q8_0.gguf` for Russian, `parakeet-tdt-0.6b-v3-Q4_K_M.gguf`), and before that through
   `parakeet-mlx` with `mlx-community/parakeet-tdt-0.6b-v3` from the Hugging Face cache; its
   `docs/asr-bakeoff.md`, `docs/speech-model-choice-plan.md` and `untracked/scripts/asr-bench/` say how
   and how fast. This works today, 150 s of audio in 12 s (tried on 2026-09-20):
   ffmpeg -y -i content/<file>.mp3 -t 150 -ac 1 -ar 16000 -sample_fmt s16 /tmp/first.wav
   /Users/mikhail/w/learning/beseda/untracked/scripts/asr-bench/transcribe.cpp/build/bin/transcribe-cli \\
     -m "$HOME/Library/Application Support/Beseda/runtime/models/gigaam-v3-e2e-rnnt-Q8_0.gguf" -l ru -q \\
     -o /tmp/first.txt /tmp/first.wav
   Wrap it in a script of this project's own; if the binary is to be relied on, copy it and the model into
   the project or say in the README where they come from. The catalog is a file in the repo a person can
   edit; entries for new files are drafted by one command and reviewed by hand.
2. Icons: one per meditation and the app icon, one family like the reference — a round ring with a
   green-to-blue gradient and a simple glyph that fits the meditation. The agents on the openai-codex
   models generate images through OpenAI image generation, and Mikhail checked that it works from here:
   make several variants of the family and of each icon, look at them next to the reference, keep the
   best, and write the choice and the rejected variants into `docs/` with a line of why. Raster in the
   asset catalog is fine; a vector drawn in code is fine too if it looks better.
3. Screens: the list (sections, rows like the reference, a checkmark on what was completed today); quick
   search that filters as you type; favorites — a heart on a row and a view of them; the player — a
   full-screen gradient, the ring with progress and the play button, the time left, scrubbing, volume;
   playback goes on with the screen locked and shows on the lock screen with controls; a meditation played to
   its end is marked completed. Favorites and completions survive a relaunch.
4. Apple Health: when a meditation plays to its end, a mindful session of its duration is written to
   HealthKit, permission asked the first time; on the simulator the Health app shows the entry.
5. New files: drop mp3s into `content/`, run one command — the catalog drafts entries for the new ones and
   the app is rebuilt with them bundled. The README says it in three lines.
6. To the iPhone: the app cannot be signed here (no Apple ID). Every setting that needs Mikhail is already
   in the project — bundle id, the HealthKit capability, background audio — and the README says exactly what
   he does: open the project, pick his team, run on the phone. Everything else is proven on the simulator by
   a tester with the kit's tools: every screen against the reference, a full play of a short file (cut a
   30-second one from the big file for the tests, never ship it), the Health entry, favorites, search.

Stack: SwiftUI, AVFoundation, HealthKit, iOS 26, no third-party packages. Mikhail is reachable through the
secretary but slow to answer: decide yourself where you can.
"""
    # run(task, power_real, Path.home() / "w/learning/ios-kit", slots=4)  # 06:31, reported green at 12:37, the kit is built
    run(meditate, power_real, Path.home() / "w/learning/meditate", slots=10, kit=IOS)
    # resume(power_real, slots=10)  # the run state/current points at, when its board is gone
