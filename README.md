# FL Studio MCP

FL Studio MCP connects an MCP client to FL Studio through a virtual MIDI port and a small controller script that runs inside FL Studio. It lets an assistant inspect and edit many parts of an open project, including transport, mixer, channels, patterns, notes, and plugin parameters.

The repository also includes an optional Windows desktop adapter. It can take screenshots, try a sample drop into the Playlist, use the Plugin Picker, and render a saved project through FL Studio's command-line renderer. Those actions depend on the visible Windows desktop and should be checked in FL Studio after they run.

This project is maintained at [prodlunaro-sketch/fl-studio-mcp](https://github.com/prodlunaro-sketch/fl-studio-mcp). It builds on the MIT-licensed work by [Zierax](https://github.com/Zierax/fl-studio-mcp) and earlier contributors. See [Credits](docs/MENTION.md) for the source projects.

## What it can do

- Control playback, recording, tempo, loop mode, and song position.
- Read and change mixer tracks, channel settings, patterns, step sequences, and piano-roll notes.
- Inspect and change parameters for plugins already loaded in the project.
- Discover functions exposed by the installed FL Studio scripting API and call them through the raw API tools.
- Read project, playlist, mixer, channel, and transport state.
- Analyze an exported audio file with FFmpeg, including loudness, peaks, duration, and silence intervals.
- On Windows, use optional desktop controls for screenshots, sample drops, plugin insertion, and rendering a saved `.flp` file.

FL Studio's scripting API cannot create a channel or load a sample into one. The Windows adapter can attempt a sample drop into the Playlist, and it can open the Plugin Picker. These UI actions need visual review. See [Limitations](docs/LIMITATIONS.md).

## Requirements

- FL Studio 20.7 or newer, with its MIDI controller scripting API.
- Python 3.10 or newer and [uv](https://docs.astral.sh/uv/).
- A virtual MIDI port: [loopMIDI](https://www.tobias-erichsen.de/software/loopmidi.html) on Windows, or the IAC Driver on macOS.
- For Windows desktop tools, Windows with FL Studio open in the same logged-in desktop session. Install the optional `windows-ui` dependencies.
- For audio analysis, `ffmpeg` and `ffprobe` available on `PATH`.

## Quick start

Clone the repository, install Python dependencies, and install the FL Studio controller script. Full Windows and macOS instructions are in [Setup](docs/SETUP.md).

```powershell
uv sync
```

For Windows desktop tools, install the optional dependencies:

```powershell
uv sync --extra windows-ui
```

Start loopMIDI and add a port. Copy `fl_controller/device_FLStudioMCP.py` into FL Studio's `Settings/Hardware/FLStudioMCP` folder, then select **FL Studio MCP Controller** for that MIDI input in FL Studio's MIDI settings. Restart FL Studio or update its MIDI scripts.

Configure your MCP client to launch the server from this repository. The command is:

```text
uv run --directory <path-to-this-repository> fl-studio-mcp
```

The exact configuration format depends on the MCP client. The setup guide includes a JSON example. After connecting, call `fl_connection_status` to check the MIDI bridge.

## Guides

| Document | Contents |
| --- | --- |
| [User guide](docs/USER_GUIDE.md) | Setup checklist, working features, examples, and known limits |
| [Setup](docs/SETUP.md) | Windows and macOS installation instructions |
| [Tool catalog](docs/TOOLS.md) | MCP tools grouped by function |
| [Architecture](docs/ARCHITECTURE.md) | MIDI and JSON bridge, controller script, and hot reload |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common connection and setup issues |
| [Limitations](docs/LIMITATIONS.md) | FL Studio API limits and Windows UI adapter scope |
| [Development](docs/DEVELOPMENT.md) | Project structure and contribution notes |

## Project layout

```text
fl_controller/                 Script loaded by FL Studio
src/fl_studio_mcp/server.py    MCP server entry point
src/fl_studio_mcp/tools/       Transport, mixer, channel, pattern, and other tools
scripts/                       Setup helpers and piano-roll script
docs/                          Setup and feature documentation
```

## License

MIT. See [LICENSE](LICENSE) and [Credits](docs/MENTION.md).

