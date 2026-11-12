"""Optional Windows desktop adapter for FL Studio operations outside its MIDI API.

This module deliberately imports GUI automation packages only when a tool is
called, so the MCP server remains usable on macOS/Linux without the optional
Windows dependencies.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from fastmcp import FastMCP

_render_jobs: dict[str, dict[str, Any]] = {}
_render_lock = threading.Lock()


def _desktop_dependencies() -> tuple[Any, Any, Any]:
    if os.name != "nt":
        raise RuntimeError("The FL Studio Windows UI adapter is available only on Windows")
    try:
        import pyautogui
        from pywinauto import Desktop
        from pywinauto.application import Application
    except ImportError as exc:
        raise RuntimeError(
            "Install the optional Windows UI dependencies with: "
            "pip install 'fl-studio-mcp[windows-ui]'"
        ) from exc
    return Desktop, Application, pyautogui


def _find_fl_window() -> Any:
    Desktop, _, _ = _desktop_dependencies()
    candidates = []
    for window in Desktop(backend="uia").windows(visible_only=True):
        try:
            title = window.window_text()
            if "FL Studio" in title:
                candidates.append(window)
        except Exception:
            continue
    if not candidates:
        raise RuntimeError("No visible FL Studio window found. Open FL Studio in this Windows session.")
    if len(candidates) > 1:
        titles = [window.window_text() for window in candidates]
        raise RuntimeError(f"More than one FL Studio window is open; close extras first: {titles}")
    return candidates[0]


def _attach_fl() -> tuple[Any, Any, Any]:
    Desktop, Application, pyautogui = _desktop_dependencies()
    window = _find_fl_window()
    app = Application(backend="uia").connect(handle=window.handle)
    return app, window, pyautogui


def _capture(window: Any, pyautogui: Any, output_dir: Path) -> str:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    destination = output_dir / f"fl-studio-{stamp}.png"
    pyautogui.screenshot().save(destination)
    return str(destination.resolve())


def _find_explorer_item(filename: str, timeout: float = 12.0) -> Any:
    Desktop, _, _ = _desktop_dependencies()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for window in Desktop(backend="uia").windows(class_name="CabinetWClass", visible_only=True):
            try:
                for child in window.descendants():
                    name = child.window_text().strip() or child.element_info.name.strip()
                    if name == filename:
                        rect = child.rectangle()
                        if rect.width() > 0 and rect.height() > 0:
                            return child
            except Exception:
                continue
        time.sleep(0.25)
    raise RuntimeError(
        f"Could not locate '{filename}' in Explorer's accessible file list. "
        "Check that Explorer opened and Windows exposed the file row."
    )


def register_windows_adapter_tools(mcp: FastMCP) -> None:
    """Register optional desktop and command-line render tools."""

    @mcp.tool()
    def fl_ui_status() -> dict[str, Any]:
        """Report whether a single visible FL Studio window is available for UI automation."""
        try:
            _, window, _ = _attach_fl()
            rect = window.rectangle()
            return {
                "connected": True,
                "window_title": window.window_text(),
                "window_rect": {
                    "left": rect.left,
                    "top": rect.top,
                    "right": rect.right,
                    "bottom": rect.bottom,
                },
                "interactive_desktop_required": True,
            }
        except Exception as exc:
            return {"connected": False, "error": str(exc), "interactive_desktop_required": True}

    @mcp.tool()
    def fl_ui_capture_screenshot(output_dir: str | None = None) -> dict[str, Any]:
        """Capture the current desktop so Playlist drop coordinates can be selected."""
        try:
            _, window, pyautogui = _attach_fl()
            target_dir = Path(output_dir).expanduser() if output_dir else Path.home() / "Pictures" / "FLStudioMCP"
            return {
                "screenshot": _capture(window, pyautogui, target_dir),
                "screen_size": list(pyautogui.size()),
                "note": "Coordinates for fl_ui_drop_sample_to_playlist are absolute desktop pixels.",
            }
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def fl_ui_drop_sample_to_playlist(
        audio_path: str,
        x: int,
        y: int,
        screenshot_dir: str | None = None,
    ) -> dict[str, Any]:
        """Drag a local audio file from Windows Explorer onto a chosen Playlist point.

        The target must be an absolute desktop pixel coordinate inside an empty
        Playlist location. Call fl_ui_capture_screenshot first. The project is
        not saved automatically; review the result and save a project copy.
        """
        source = Path(audio_path).expanduser().resolve()
        if not source.is_file():
            return {"error": "Audio file not found", "audio_path": str(source)}
        try:
            _, fl_window, pyautogui = _attach_fl()
            screen_width, screen_height = pyautogui.size()
            if not (0 <= x < screen_width and 0 <= y < screen_height):
                return {"error": "Drop point is outside the desktop", "screen_size": [screen_width, screen_height]}

            # Explorer selects the exact item, which lets UI Automation locate
            # the file row instead of assuming its position in a folder view.
            subprocess.Popen(["explorer.exe", "/select,", str(source)], close_fds=True)
            item = _find_explorer_item(source.name)
            rect = item.rectangle()
            start = (int((rect.left + rect.right) / 2), int((rect.top + rect.bottom) / 2))
            fl_window.set_focus()
            # Re-focus Explorer to initiate a real shell file drag, then return
            # the pointer to FL Studio's calibrated destination.
            item.click_input(button="left")
            pyautogui.moveTo(start[0], start[1], duration=0.15)
            pyautogui.dragTo(x, y, duration=0.8, button="left")
            time.sleep(1.0)
            folder = Path(screenshot_dir).expanduser() if screenshot_dir else Path.home() / "Pictures" / "FLStudioMCP"
            screenshot = _capture(fl_window, pyautogui, folder)
            return {
                "submitted": True,
                "audio_path": str(source),
                "drop_point": {"x": x, "y": y},
                "screenshot": screenshot,
                "verify_manually": "Confirm the new Audio Clip is visible in the intended Playlist track and bar, then save a copy of the project.",
            }
        except Exception as exc:
            return {"error": str(exc), "audio_path": str(source)}

    @mcp.tool()
    def fl_ui_insert_plugin(plugin_name: str, destination: str = "channel") -> dict[str, Any]:
        """Search FL Studio's Plugin Picker and activate the named plugin.

        For destination='effect', select the target Mixer track before calling.
        Plugin names must already be scanned into FL Studio's Plugin Picker.
        """
        if destination not in {"channel", "effect"}:
            return {"error": "destination must be 'channel' or 'effect'"}
        if not plugin_name.strip():
            return {"error": "plugin_name must not be empty"}
        try:
            _, window, pyautogui = _attach_fl()
            window.set_focus()
            pyautogui.press("f8")
            time.sleep(0.4)
            pyautogui.write(plugin_name, interval=0.02)
            time.sleep(0.3)
            pyautogui.press("enter")
            time.sleep(1.0)
            folder = Path.home() / "Pictures" / "FLStudioMCP"
            screenshot = _capture(window, pyautogui, folder)
            return {
                "submitted": True,
                "plugin_name": plugin_name,
                "destination": destination,
                "screenshot": screenshot,
                "verify_manually": "Confirm the plugin window or channel/effect slot appeared. Plugin Picker navigation can vary by FL version and picker state.",
            }
        except Exception as exc:
            return {"error": str(exc)}

    @mcp.tool()
    def fl_render_project(
        project_path: str,
        output_dir: str,
        filename: str,
        format: str = "wav",
    ) -> dict[str, Any]:
        """Start a background FL Studio command-line render of a saved project."""
        project = Path(project_path).expanduser().resolve()
        output = Path(output_dir).expanduser().resolve()
        if not project.is_file() or project.suffix.lower() != ".flp":
            return {"error": "project_path must point to an existing .flp file", "project_path": str(project)}
        extension = format.lower().lstrip(".")
        if extension not in {"wav", "mp3", "ogg", "flac", "m4a"}:
            return {"error": "format must be wav, mp3, ogg, flac, or m4a"}
        if not filename or Path(filename).name != filename or Path(filename).suffix:
            return {"error": "filename must be a simple file name without an extension or directory"}
        if not output.exists():
            return {"error": "output_dir must already exist", "output_dir": str(output)}

        configured_exe = os.environ.get("FL_STUDIO_EXE")
        candidates = [
            Path(configured_exe) if configured_exe else None,
            Path(r"C:\Program Files\Image-Line\FL Studio 2024\FL64.exe"),
            Path(r"C:\Program Files\Image-Line\FL Studio 2025\FL64.exe"),
        ]
        exe = next((path for path in candidates if path and path.is_file()), None)
        if exe is None:
            return {"error": "FL64.exe not found; set FL_STUDIO_EXE to its full path"}

        output_file = output / f"{filename}.{extension}"
        job_id = uuid.uuid4().hex[:12]
        command = [str(exe), f"/R{filename}", f"/E{extension}", f"/O{output}", str(project)]
        try:
            process = subprocess.Popen(
                command,
                cwd=str(exe.parent),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
        except OSError as exc:
            return {"error": f"Could not start FL Studio render: {exc}"}
        with _render_lock:
            _render_jobs[job_id] = {
                "process": process,
                "project": str(project),
                "output": str(output_file),
                "started_at": time.time(),
            }
        return {
            "job_id": job_id,
            "status": "running",
            "project": str(project),
            "expected_output": str(output_file),
            "note": "FL Studio renders the saved project in a separate process. Check status with fl_render_status.",
        }

    @mcp.tool()
    def fl_render_status(job_id: str) -> dict[str, Any]:
        """Check a render job and return the output path once FL Studio exits."""
        with _render_lock:
            job = _render_jobs.get(job_id)
        if job is None:
            return {"error": "Unknown render job id", "job_id": job_id}
        process = job["process"]
        return_code = process.poll()
        output_path = Path(job["output"])
        if return_code is None:
            return {"job_id": job_id, "status": "running", "elapsed_seconds": round(time.time() - job["started_at"], 1)}
        with _render_lock:
            _render_jobs.pop(job_id, None)
        if return_code != 0:
            return {"job_id": job_id, "status": "failed", "return_code": return_code, "output": str(output_path)}
        return {
            "job_id": job_id,
            "status": "completed" if output_path.is_file() else "process_exited_output_missing",
            "return_code": return_code,
            "output": str(output_path),
            "size_bytes": output_path.stat().st_size if output_path.is_file() else None,
        }
