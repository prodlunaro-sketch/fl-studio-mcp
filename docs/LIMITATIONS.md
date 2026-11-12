# Limitations

This is the honest list of what FL Studio's scripting API allows — and
crucially, what it does **not**. Read it once, and you will not waste prompts
on things the server can never do.

## Not available through FL's MIDI scripting API

### Create channels or load audio files

There is no documented FL API function to:

- add a new channel to the channel rack,
- load a sample / audio file into a channel,
- instantiate a plugin.

The optional Windows UI adapter can attempt to drag a sample from Explorer
into the Playlist. It requires FL Studio visible in the logged-in desktop,
fresh screenshot coordinates, and manual review; it does not automatically
save the project. Adding a sample as a channel still requires manual UI work.

### Place clips on the playlist timeline

`playlist` API functions cover track names, colors, mute/solo and state
reads. There is no API call to drop a pattern clip or audio clip onto the
timeline. The optional Windows UI adapter can attempt a sample drop at a
specified screen point, but cannot guarantee the intended track/bar without
visual review. Pattern *management* (create/select/rename/clone/clear) is
available through the MIDI API.

### Load or instantiate plugins

Plugins already present in the project can be controlled (params, presets,
colors). The optional Windows UI adapter can search FL Studio's Plugin Picker
and submit the selected name, but the exact result must be checked in FL.
Some 3rd-party VSTs don't report parameter names; `fl_get_plugin_params` will
return indices/values, and `fl_plugin_param_name_to_index` can resolve names.

### Persist live note triggers

`fl_trigger_note` plays audio through the channel as a preview. Unless FL
recording is active, this is **not** written into the pattern — consistent
with FL's own behavior. For written music, use the step sequencer or piano
roll tools.

### Read audio waveform through the MIDI API

The MIDI API is control-plane only. There is no "get audio samples" or
"render to file" call. On Windows, `fl_render_project` uses FL Studio's
documented command-line renderer on a saved `.flp` project; it renders in a
separate process and `fl_render_status` reports the result. This does not
render unsaved changes from the currently open project.

## Partial / version-dependent

| Area | Reality |
|------|---------|
| API surface | FL's Python API has grown over versions; some functions exist only in newer builds. Use `fl_api_list_functions` to discover what *your* FL Studio exposes. |
| Plugin params | Names, ranges, and units are plugin-provided; not all plugins cooperate. |
| UI automation | `ui.*` functions (focus forms, browser navigation, popup menus) exist and are exposed via raw access, but they depend on the window being open (e.g. browser must be visible and focused). |
| Preview = state change | Some `ui.*`/transport functions mutate FL's visible state — the server always reads back and returns the authoritative value. |

## Performance & safety

- One JSON round-trip per call; each takes a few ms inside FL Studio. Batch
  heavy work (e.g. whole patterns) into single calls rather than many small
  ones.
- The controller executes commands synchronously in FL's script thread — do
  not run thousands of calls in a tight loop while playback is active.
- Undo: the server can save/restore undo points (`fl_save_undo`, `fl_undo`),
  but FL's undo count/stack depends on its own "undoable" model — big
  scripted edits may coalesce. Save the project (Ctrl+S) before risky
  experiments, or snapshot with `fl_project_snapshot`.
