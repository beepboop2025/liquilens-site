"""Credential-free build process and bounded artifact boundaries."""

import os
from pathlib import Path
import signal
import stat
import subprocess
import time

BUILDER_UID = 10001


def clean_env(extra=None):
    env = {"PATH": "/usr/local/bin:/usr/bin:/bin", "PYTHONDONTWRITEBYTECODE": "1",
           "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
           "GIT_TERMINAL_PROMPT": "0", "GIT_CONFIG_COUNT": "1",
           "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": "/dev/null",
           "WRANGLER_SEND_METRICS": "false"}
    env.update(extra or {})
    return env


def quiesce_builder():
    for _ in range(100):
        subprocess.run(["pkill", "-KILL", "-u", str(BUILDER_UID)],
                       capture_output=True, check=False)
        found = subprocess.run(["pgrep", "-u", str(BUILDER_UID)],
                               capture_output=True, check=False)
        if found.returncode == 1:
            return
        if found.returncode != 0:
            raise RuntimeError("Cannot inspect builder processes")
        time.sleep(0.05)
    raise RuntimeError("Builder processes remain alive")


def run(args, cwd, *, builder=False, capture=False, timeout=600, extra=None):
    if builder:
        args = ["setpriv", "--reuid=10001", "--regid=10001", "--init-groups",
                "--no-new-privs", *args]
    process = subprocess.Popen(args, cwd=cwd, env=clean_env(extra),
                               start_new_session=True, text=True,
                               stdout=subprocess.PIPE if capture else None)
    try:
        output, _ = process.communicate(timeout=timeout)
        if process.returncode:
            raise RuntimeError(f"Command {args[0]} failed: {process.returncode}")
        return output.strip() if capture else None
    finally:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)
        if builder:
            quiesce_builder()


def read_regular(path, limit, *, allow_empty=False):
    """Read the same bounded, single-link descriptor that was inspected."""
    path = Path(path)
    for parent in path.parents:
        if parent.is_symlink():
            raise RuntimeError("Symlink artifact ancestor")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise RuntimeError("Artifact is not a single-link regular file")
        if not (0 if allow_empty else 1) <= info.st_size <= limit:
            raise RuntimeError("Artifact exceeds size bound")
        data = stream.read(limit + 1)
        if len(data) != info.st_size:
            raise RuntimeError("Artifact changed while reading")
        return data


def copy_tree(source, destination):
    source = Path(source)
    for ancestor in (source, *source.parents):
        if not stat.S_ISDIR(ancestor.lstat().st_mode):
            raise RuntimeError("Source tree root or ancestor is not a plain directory")
    count = size = 0
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        if ".git" in relative.parts:
            continue
        if path.is_symlink():
            raise RuntimeError("Source tree contains a symlink")
        if path.is_dir():
            (destination / relative).mkdir(parents=True, exist_ok=True)
        else:
            data = read_regular(path, 64 * 1024 * 1024, allow_empty=True)
            count += 1
            size += len(data)
            if count > 20000 or size > 500 * 1024 * 1024:
                raise RuntimeError("Source tree exceeds copy bound")
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
