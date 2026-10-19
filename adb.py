"""Thin wrapper around `adb` commands."""

import random
import shlex
import subprocess
import time

import config


def _run(args: list[str], capture: bool = False) -> bytes | None:
    cmd = ["adb"] + args
    if capture:
        result = subprocess.run(cmd, capture_output=True, check=True)
        return result.stdout
    subprocess.run(cmd, check=True)
    return None


def check_device() -> str:
    """Raise if no device is connected. Return the serial of the first device."""
    out = _run(["devices"], capture=True).decode()
    lines = [l for l in out.splitlines()[1:] if l.strip() and "\tdevice" in l]
    if not lines:
        raise RuntimeError(
            "No ADB device found. Start your emulator and run `adb devices`."
        )
    return lines[0].split("\t")[0]


def foreground_package() -> str:
    """Return the package name of the app currently in front ("" if unknown)."""
    out = _run(["shell", "dumpsys", "activity", "activities"], capture=True).decode(errors="ignore")
    for line in out.splitlines():
        if "topResumedActivity" in line or "mResumedActivity" in line:
            for tok in line.split():
                if "/" in tok:
                    return tok.split("/")[0]
    return ""


def recover_to_hinge() -> None:
    """Get off a popup / other app: press Back, and if that left Hinge
    (home screen, Chrome), relaunch Hinge. Never taps on the popup itself,
    so it can't hit a purchase button or a link."""
    press_back()
    time.sleep(3)
    if foreground_package() != "co.hinge.app":
        _run(["shell", "monkey", "-p", "co.hinge.app", "-c",
              "android.intent.category.LAUNCHER", "1"], capture=True)
        time.sleep(6)


def press_back() -> None:
    _run(["shell", "input", "keyevent", "KEYCODE_BACK"])


def screenshot() -> bytes:
    """Return PNG bytes of the current screen."""
    return _run(["exec-out", "screencap", "-p"], capture=True)


def tap(x: int, y: int) -> None:
    _run(["shell", "input", "tap", str(x), str(y)])


def input_text(text: str) -> None:
    """Type `text` into the currently focused field via `adb shell input text`.

    Single-quotes the payload with shlex so $, `, ", and spaces survive the
    device shell. Caller should keep text plain ASCII — emoji and the chars
    \\ " $ ` should be filtered upstream (the model is instructed to avoid
    them) since `input text` itself only sends keyevents.
    """
    quoted = shlex.quote(text)
    _run(["shell", f"input text {quoted}"])


def swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
    _run(["shell", "input", "swipe",
          str(x1), str(y1), str(x2), str(y2), str(duration_ms)])


def scroll_down() -> None:
    c = config.COORDS
    swipe(*c["scroll_from"], *c["scroll_to"], c["scroll_duration_ms"])


def scroll_up() -> None:
    c = config.COORDS
    swipe(*c["scroll_to"], *c["scroll_from"], c["scroll_duration_ms"])


def jitter_sleep(key: str) -> None:
    lo, hi = config.DELAYS[key]
    time.sleep(random.uniform(lo, hi))
