import os
import subprocess
import sys

from factory.tools.processes import kill_processes_of_thread


def test_what_a_thread_started_dies_with_it() -> None:
    # a system binary (sleep) hides its environment from ps on macOS; a server is python
    server = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], env={**os.environ, "BB_THREAD_ID": "thr_gone"})
    bystander = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], env={**os.environ, "BB_THREAD_ID": "thr_gone2"})

    killed = kill_processes_of_thread("thr_gone")

    assert killed == [server.pid] and server.wait(timeout=5) < 0
    assert bystander.poll() is None
    bystander.kill()
