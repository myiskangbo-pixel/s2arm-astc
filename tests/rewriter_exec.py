#!/usr/bin/env python3
"""Keep REW=<Python script or native executable> usable by the existing tests."""
import os
import subprocess
import sys
from pathlib import Path

rew, *args = sys.argv[1:]
command = [sys.executable, rew, *args] if Path(rew).suffix == '.py' else [rew, *args]
if os.name == "nt":
    # CPython's Windows execv path does not reliably preserve native child
    # exit codes through the MSYS/Git Bash test launcher. Run and propagate
    # the exact child status instead; stdout/stderr remain inherited.
    raise SystemExit(subprocess.run(command, check=False).returncode)
os.execv(command[0], command)
