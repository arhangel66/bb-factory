"""What a thread's agent left running, found by the BB_THREAD_ID every process it started inherits."""

import os
import signal
import subprocess


def kill_processes_of_thread(thread: str) -> list[int]:
    # every process whose environment carries the thread's id: a server the agent started and left behind
    listing = subprocess.run(["ps", "-E", "-axo", "pid=,command="], capture_output=True, text=True, timeout=30).stdout
    killed = []
    for line in listing.splitlines():
        pid, _, command = line.strip().partition(" ")
        if f"BB_THREAD_ID={thread} " in command + " " and int(pid) != os.getpid():
            try:
                os.kill(int(pid), signal.SIGTERM)
                killed.append(int(pid))
            except ProcessLookupError:
                pass  # gone between the listing and the kill
    return killed
