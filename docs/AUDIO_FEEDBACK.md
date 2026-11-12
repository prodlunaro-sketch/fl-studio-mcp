# Audio feedback and automation scope

This fork adds local analysis of exported mixes as the first feedback-loop
component. `fl_analyze_export` calls FFmpeg and ffprobe on a file chosen by the
user and returns loudness, peak, format, and silence measurements. It does not
upload the audio or modify the FL Studio project.

`fl_compatibility_report` discovers the modules and functions exposed by the
running FL Studio build and marks supported, partial, and unavailable core
features. This avoids assuming that all releases expose the same API surface.

## Backward compatibility

The upstream bridge advertises FL Studio 20.7+; the local target machine has
FL Studio 2024 version 24.1.2.4394. The controller discovers the API surface
at runtime instead of requiring one fixed API version. Tempo writes use the
new `mixer.setCurrentTempo` call when it is available and fall back to the
long-standing `general.processRECEvent` + `midi.REC_Tempo` route otherwise.
Both paths read the tempo back and only report success when the value matches.

Compatibility remains feature-by-feature: newer Playlist, plugin, and mixer
functions may not exist on older builds. `fl_compatibility_report` reports
those gaps rather than advertising unsupported controls as available.

## What can be automated with the current bridge

- Inspect a project and change supported mixer, plugin, pattern, and Piano
  Roll values through the existing MIDI-script bridge.
- Analyze a rendered audio file after export, then use its measurements to
  recommend a bounded revision.

## Windows UI adapter

The optional `windows-ui` extra adds desktop tools for taking a screenshot,
dragging an Explorer audio file to an explicitly chosen Playlist coordinate,
and submitting a plugin name through FL's Plugin Picker. These actions require
an interactive logged-in desktop with FL Studio visible. The sample-drop tool
does not save the project and returns a screenshot for review. UI behavior
depends on window focus, scaling, picker state, and FL build; inspect each
result before saving.

`fl_render_project` starts FL Studio's documented command-line renderer for a
saved `.flp` project and returns a job ID; `fl_render_status` polls the result.
It renders the saved file in a separate FL Studio process, not unsaved edits in
the open window.

## What still needs a separate adapter

The documented FL Studio scripting API does not provide calls to create or
load channels. The Windows adapter covers an initial sample-to-Playlist path
and Plugin Picker path, but still needs validation against each FL build and
window configuration. UI automation depends on focus, display scaling, and
dialog layout, so it remains optional and returns screenshots for review.

Suggested integration stages:

1. Detect the installed FL Studio version and available scripting functions.
2. Validate the Windows UI adapter for adding a sample/plugin and placing a
   Playlist clip on the installed FL build.
3. Run a saved-project CLI render and check for the completed file.
4. Run `fl_analyze_export` and feed its measurements into a bounded revision
   plan.

The audio analyzer requires `ffmpeg` and `ffprobe` on `PATH`.
