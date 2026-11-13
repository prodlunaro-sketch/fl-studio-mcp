# User guide

This guide describes the features currently present in the repository and how to use them. The MIDI bridge talks to FL Studio's scripting API. A separate optional Windows adapter controls parts of the visible desktop. The desktop actions are best treated as assisted actions: check their result in FL Studio and save the project yourself.

## 1. Install and connect

### Windows

1. Install FL Studio 20.7 or newer, Python 3.10 or newer, [uv](https://docs.astral.sh/uv/), and [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html).
2. Start loopMIDI and create a port, for example `FLStudioMCP`.
3. From the repository directory, install the server:

   ```powershell
   uv sync
   ```

   To enable the desktop adapter as well:

   ```powershell
   uv sync --extra windows-ui
   ```

4. Copy `fl_controller/device_FLStudioMCP.py` into:

   ```text
   %USERPROFILE%\Documents\Image-Line\FL Studio\Settings\Hardware\FLStudioMCP\
   ```

   Create the `FLStudioMCP` folder if it does not exist. Restart FL Studio or use **Options → Update MIDI scripts**.
5. In **Options → MIDI Settings**, select the loopMIDI port as an input, set its controller type to **FL Studio MCP Controller**, and enable it.
6. Add the MCP server to your MCP client. For a client that accepts the common JSON `mcpServers` format, use this and replace the path:

   ```json
   {
     "mcpServers": {
       "fl-studio": {
         "command": "uv",
         "args": ["run", "--directory", "C:\\CODE\\FLStudio-MCP", "fl-studio-mcp"]
       }
     }
   }
   ```

   Some clients use a different configuration format. The equivalent server command is `uv run --directory <repository-path> fl-studio-mcp`.
7. Keep FL Studio and loopMIDI open. In the MCP client, call `fl_connect`, then `fl_connection_status`.

### macOS

Install the Python dependencies with `uv sync`, enable the IAC Driver in **Audio MIDI Setup**, and copy the controller script to `~/Documents/Image-Line/FL Studio/Settings/Hardware/FLStudioMCP/`. Select the IAC port and **FL Studio MCP Controller** in FL Studio's MIDI settings. Use a macOS repository path in your MCP client's server configuration. The Windows desktop adapter is not available on macOS.

For the optional piano-roll helper, copy `scripts/ComposeWithLLM.pyscript` into FL Studio's **Piano roll scripts** folder, update MIDI scripts, and assign the `ComposeWithLLM` script to `Ctrl+Alt+Y` on Windows or `Cmd+Opt+Y` on macOS. This is needed by the piano-roll tools that trigger the helper script.

See [Setup](SETUP.md) for the install script and more detailed setup notes.

## 2. Check the connection and FL Studio version

Use `fl_connect` to open the MIDI port, then `fl_connection_status` to see whether the bridge is connected. `fl_compatibility_report` reports the FL Studio API version, available modules, and which features were detected. The API surface depends on the FL Studio version installed on the computer.

If the bridge does not connect, confirm that FL Studio has loaded the controller script, the loopMIDI port is enabled, and both applications are running in the same Windows session. FL Studio's **View → Script output** should show that the controller initialized.

## 3. MIDI/API features

The standard server provides tools in these areas:

- **Transport:** play, stop, record, tempo, loop mode, playback speed, song position, and transport status.
- **Mixer:** read track names and state, set volume and pan, mute, solo, arm, change color, route channels, inspect peaks, and work with supported routing and EQ functions.
- **Channel rack:** inspect and select channels, set channel volume, pan, name, color, pitch, mute, solo, routing, and step data.
- **Patterns:** list, create, select, rename, clone, clear, and set pattern length.
- **Step sequencer:** read, write, or clear per-step note and parameter data.
- **Piano roll:** send, inspect, and delete notes; add chords; clear notes; and inspect piano-roll state. The helper script and its shortcut must be configured for note-writing tools that use it.
- **Plugins:** inspect plugins already in the project, read and set exposed parameter values, navigate presets, and read plugin colors.
- **Project and API inspection:** get project and arrangement state, use undo helpers, inspect constants and functions exposed by FL Studio, and call supported raw API functions.
- **Playlist tracks:** inspect and change supported track-level state such as names, colors, mute, solo, and selection.

Tool names and arguments are listed in [Tool catalog](TOOLS.md). Most indices are zero-based. Volume and pan values generally use `0.0` to `1.0`; consult the individual tool description for its units.

### Example requests

```text
Connect to FL Studio and report the tempo and transport state.
Set the tempo to 128 BPM and switch loop mode to song.
List the mixer tracks, then set track 3 to 80% volume and pan it slightly left.
Create a pattern called Intro and program a kick on steps 0, 4, 8, and 12.
Read the parameters of the plugin on channel 0, then set parameter 4 to 0.35.
```

`fl_trigger_note` is for audible preview. It does not write a note into the pattern unless FL Studio is recording. Use the piano-roll or step-sequencer tools for notes that should remain in the project.

## 4. Optional Windows desktop adapter

Install with `uv sync --extra windows-ui`. FL Studio must be visible in the same logged-in desktop session as the MCP server. The adapter uses screen coordinates for some actions; window size, scaling, focus, and FL Studio layout can affect the result.

| Tool | What it does | What to check |
| --- | --- | --- |
| `fl_ui_status` | Checks for a visible FL Studio window | Confirm the expected project/window is open |
| `fl_ui_capture_screenshot` | Saves a screenshot to a directory | Use a current screenshot to choose screen coordinates |
| `fl_ui_drop_sample_to_playlist` | Opens Explorer and attempts to drag an audio file onto a Playlist position | Inspect the drop and save a project copy manually |
| `fl_ui_insert_plugin` | Opens the Plugin Picker, searches for a name, and submits the selection | Confirm the intended plugin appeared; choose the mixer track first for an effect |
| `fl_render_project` | Starts a command-line render of a saved `.flp` in a separate FL Studio process | Check `fl_render_status` and listen to the output |
| `fl_render_status` | Reports the state and output path of a render job | Verify that the output file plays correctly |

### Drop a sample into the Playlist

1. Open the intended project in FL Studio and call `fl_ui_status`.
2. Call `fl_ui_capture_screenshot` and read the returned image path. Open that image to identify the absolute screen pixel coordinates for the Playlist drop point.
3. Call `fl_ui_drop_sample_to_playlist` with the sample's full path, the chosen `x` and `y`, and an optional screenshot directory.
4. Check the Playlist in FL Studio. The tool does not save the project, and it may miss if the window layout or focus changes. Save a copy after confirming the result.

The action attempts to place the sample as a Playlist clip. It does not add a sampler channel to the Channel Rack.

### Insert a plugin

Call `fl_ui_insert_plugin` with the plugin's name and destination (`channel` or `mixer`). The tool uses the Plugin Picker and keyboard input. For an effect, first select the target mixer track in FL Studio. Confirm the inserted plugin manually. After insertion, the normal plugin tools can inspect or change parameters that FL Studio exposes.

### Render a saved project

Save the `.flp` first and ensure the output directory already exists. Call `fl_render_project` with the project path, output directory, filename, and format, then poll using the returned job ID with `fl_render_status`. The render runs in a separate FL Studio process and does not include unsaved changes from the currently open project. The adapter detects common FL Studio 2024 and 2025 install paths; set `FL_STUDIO_EXE` if your executable is installed elsewhere.

These desktop functions are implemented in the repository but have not been verified against every FL Studio installation and desktop layout.

## 5. Analyze an audio export

`fl_analyze_export` runs local FFmpeg tools against an audio file. Install `ffmpeg` and `ffprobe` and make sure both commands work from the terminal. The report includes file and codec details, duration, integrated loudness (LUFS), loudness range, true or sample peak, mean volume, and detected silence intervals. Analysis is performed on an exported file; it does not read live audio from FL Studio.

## 6. Limits and recovery

- The MIDI scripting API cannot create a Channel Rack channel or load a sample into one.
- Playlist clip placement is not exposed through the MIDI API. The Windows adapter can attempt a desktop drag and drop, which needs manual review.
- The Plugin Picker action is UI automation. Plugin names, picker focus, and window layout can affect it.
- The renderer uses a saved project file. Save changes before rendering.
- Some API functions vary by FL Studio version. Check `fl_compatibility_report` or discover functions with the API tools.
- Save a project copy before large scripted edits. FL Studio's undo behavior can vary by operation.

More details are in [Limitations](LIMITATIONS.md) and [Troubleshooting](TROUBLESHOOTING.md).

