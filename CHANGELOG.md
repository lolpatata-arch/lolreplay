# Changelog

## Unreleased — Smart library (1.3 development)

- Persistent local favorites, manually assigned games and tags using SQLite.
- Search by clip name, game or tags; filter favorites and games.
- Preserve metadata when renaming clips within the application.
- No recording changes or automatic media deletion.
- GUI and desktop verification pending.

## 1.2.0 — Manual updates (preview)

- Add opt-in update checks, version selection, release notes and explicit confirmation in Settings.
- Stable releases only by default; optional preview releases.
- Verify official ZIP digest and archive paths; check dependencies and recorder status before updating.
- Transactional rollback for caught installer errors; retain backups.
- No automatic network checks, no changes to recording logic.
- GUI and live release-download validation pending.

## 1.1.0 — Layout stability

- Isolate hidden-page size hints from the active workspace.
- Adapt library and editor splitters to usable logical width and height; preserve manually adjusted split sizes until orientation changes.
- Keep native video outside scroll areas; allow smaller video and controls, and bound long combo-box text.
- Reflow controls and theme tiles on compact windows.
- Expand the release test matrix; live Qt/Wayland verification is required before stable release.
- Recording, audio, storage and export logic unchanged.

## 1.0.4 — Library layout hotfix

- Keep library playback outside scroll areas, with a separate scrollable playback and management controls panel.
- Remove rigid library splitter height and allow the video preview to shrink on small displays.
- Preserve the editor fix, direct seeking, existing preferences and recording behavior.
- Library fix awaiting live Wayland verification.

## 1.0.3 — Editor layout hotfix

- Keep the native editor video surface outside scroll areas; scroll trim, audio and export controls separately.
- Preserve the responsive layout and direct seeking from 1.0.2.
- No functional recording, audio routing, storage or export engine changes.
- Editor layout fix confirmed by the maintainer on Debian 13 / Hyprland; Arch UI retest pending.

## 1.0.2 — Responsive desktop

- Adapt to logical window size and accessibility scaling; compact navigation, scrollable workspaces and stacked panels on narrow windows.
- Absolute click and drag seeking in library and fullscreen playback; improve editor trim-handle hit testing.
- Reorganize settings into ten categories with desktop navigation and a compact selector; group internal shortcuts.
- Preserve recording, audio, storage, external drive recovery and existing preferences.
- Arch/AMD and Debian/Intel capture verified by the maintainer in 1.0.1; new UI needs live testing.

## 1.0.1 — Encoder compatibility

- Retry in CQP when the current recorder explicitly rejects CBR; retain CBR on compatible hardware.
- Select automatic, CBR or CQP rate control from settings or CLI.
- Create the default local library on install without recreating missing external libraries.
- Correct the diagnostic version and document the tested Debian setup.
- Debian capture was confirmed with the manual 1.0.0 workaround; the new automatic retry needs live testing.

## 1.0.0 — First public release

- First public release of the user-tested 0.9.9.1 feature set.
- Unified version labels, public installation documentation and credits.
- Niri remains experimental; no universal distribution compatibility claim.

## 0.9.9.1

- Editable internal keyboard shortcuts and optional shortcuts for additional clip/editor actions.
- Global replay key setup with configuration backups and conservative conflict checks.
- Translated shortcut settings in all nine languages.

## 0.9.9

- Sixteen validated, persistent interface preferences, translated into all nine supported languages.
- Text scaling, contrast, focus visibility, control size, thumbnails, playback, startup and polling controls.
- Reset only these preferences; leave recorder, clips, language and theme intact.
- Preserve the 0.9.8 translation scope hotfix.

## 0.9.8

- Nine interface languages; choose in Settings / Appearance, then reopen the UI.
- Native Qt dialog translation when the platform provides Qt translation files.
- Recorder output and technical logs remain in their original language.

## 0.9.7

- Quality-of-life improvements to the library, navigation and playback.
- Fix compositor detection call and version mismatch.

## 0.9.6

- Refresh desktop launcher icon paths and preserve old icon backups.
- Keep existing desktop entry ID.

# Historical release notes

These notes describe older releases and may contain superseded instructions, including the retired artwork. Use README.md for current instructions.

# lolreplay 0.9.3

Local instant replay frontend for the already-installed Crimson Clips engine.

## Install on Arch

`sudo pacman -S --needed pyside6 qt6-wayland qt6-multimedia qt6-multimedia-ffmpeg ffmpeg`

Close any old lolreplay window, then run `python3 install.py` and `lolreplay`. Existing recorder, F8 configuration, clip paths and microphone settings are preserved. Closing the UI does not stop replay. The installer keeps backups of modified executables and desktop entry. The desktop entry ID stays crimson-clips to preserve dock pins.

## 0.3.1 visual update

- Featured latest clip, custom-drawn media tiles, compact replay controls and storage usage indicator.
- Theme previews in Settings; existing theme choice is preserved.
- Existing recorder, shortcut, clip path and microphone configuration are not modified.
- Tested for Python syntax and installation with a temporary home. Qt rendering and actual media playback must be validated on the target Linux desktop.

## Features

- Replay dashboard, four duration buttons, real recorder status and recent clip thumbnails.
- Library search and integrated Qt Multimedia playback with seek and volume; external-player fallback.
- Themes, existing CLI commands, existing clip folder and no uploads.
- `lolreplay --version` reports the installed release.

See 0.5 notes below for experimental microphone and external storage. Niri, long-session reliability and actual Qt playback on target hardware remain untested. Existing F8 behavior is unchanged. Qt multimedia availability and codec support depend on the system.

## Artwork

The supplied orb is a modification of FreeBSD branding for personal testing only. The MIT license applies to code, not the orb; obtain applicable permission or replace it before public distribution. This project is not affiliated with FreeBSD.

## 0.4 — Editor

Same 0.3.1 visual base, new Editor tab. Open a clip from Library or via the file chooser. Drag trim handles, scrub the timeline, or enter IN/OUT in seconds. Play selection previews the source only; export applies audio controls and optionally loops a local music file. Original audio tracks are combined in the new MP4 (not in the original). Export uses CPU H.264 (libx264), AAC, and an asynchronous cancellable FFmpeg process. Output is published only on success and never overwrites an existing file. Use a local Linux filesystem supporting hard links; external storage is still deferred. Rename is no-overwrite; Move to trash uses Qt's system trash, with no permanent-delete fallback. Do not edit recordings that are still being written. Microphone issue and Niri support remain deferred. The orb remains for personal testing only.

Rollback: close the UI and run `python3 ~/Projects/lolreplay-0.3.1/install.py`. The recorder, F8, media, and preferences remain unchanged.

## 0.4.1 — Direct editing

Editor reads the same configured clip directory as Library, and shows its videos in a thumbnail selector. Entering Editor opens the newest clip if no edit is loaded. Existing selections and trim settings are preserved on library refresh; choosing another clip resets trim. Replay also has an Edit clip button. Export saves a new `-edit.mp4` (or `-edit-2.mp4`, etc.) directly into the library with no file picker. The local music picker remains optional. Export still requires a local filesystem supporting hard links and never overwrites existing files. Recorder, F8 and configuration are unchanged.

## 0.4.2 — Dark UI polish

Keeps the 0.4.1 layout and editor. Uses Qt Fusion with an application-wide dark palette and styles for transient dialogs, spin boxes, combo boxes, menus, tooltips, focus and scrollbars. Native file dialogs are disabled within lolreplay only. Hyprland window decorations are controlled by the compositor and are not changed. No recorder, clip storage, F8 or export changes. Qt runtime appearance still needs target desktop validation. Rollback: run `python3 ~/Projects/lolreplay-0.4.1/install.py` after closing the UI.


## 0.5 — experimental microphone and protected library

Stop replay before installing (save anything you need first). This release updates the engine at the existing path, preserving the F8 binding and keeping timestamped backups. Settings now includes Change folder, Recovery folder, Choose microphone and Enable/Disable microphone. Changes require stopping replay, which clears the RAM buffer. The microphone is off by default for a fresh configuration. The optional bridge uses session-only PipeWire-Pulse modules, mixing the virtual monitor with system audio. It does not edit shell, WirePlumber or PipeWire configuration; the physical microphone is still opened by the loopback. Modules are removed on normal stop and the watchdog attempts cleanup on unexpected recorder exit. If needed run `lolreplay stop` again. The OSD workaround needs a real G733/Hyprland test. Audio bridge failures prevent start rather than silently recording without voice. Stop replay when you do not need the mic.

Choose the mounted destination folder from Settings while stopped. A hidden library identity marker prevents confusion with an empty mountpoint; do not delete it. Existing custom paths must be selected again. A registered library uses the internal recovery folder for staging, then publishes completed clips without overwrite. If a transfer fails the local copy remains; use Settings > Recovery folder to retrieve it. There is no automatic retry or migration of earlier clips. Editor exports also stage locally. Keep enough free space on the internal drive. Actual hot-unplug behavior, exFAT/NTFS support and Qt rendering need target-system tests. Do not intentionally unplug a disk while writing; safely unmount it instead.

Rollback: stop replay with `lolreplay stop`, close UI, reinstall 0.4.2 and restore the timestamped `crimson-clips.bak-*` engine backup created by this installer. The 0.4.2 installer alone does not restore the engine. Select the desired output directory before restarting the old engine; it lacks the new disk guard.

## 0.5.1 — Drive discovery
Settings > Detected drives lists data filesystems from lsblk, including unmounted external devices, and opens the folder picker at their actual mountpoint. Explicitly confirm mounting via udisksctl (udisks2, with system permissions, no sudo). Existing Change folder also shows mounted drives in its sidebar. Choose or create a writable clip folder on the drive. No format, partition or permission changes are made. The original 0.5 engine, audio bridge, recovery/publish and editor code are unchanged. System filesystems, unsupported filesystems and locked encrypted devices are not listed; unlock in the system first. Detection uses lsblk rather than guessing mountpoint paths; no automount or automatic migration. Actual device mounting and GUI rendering require target testing.

## 0.6 — Appearance, audio routing and in-place editing

Stop replay before installing; save important buffered footage first. If the old stop command throws KeyError: index after stopping the recorder, check `lolreplay status` before installing. The new audio cleanup uses the numeric IDs from `pactl list short modules`, and verifies the unique bridge name and module type before unloading. The working loopback topology is unchanged. Output selection chooses which playback device monitor to record, not the system's playback route or the player's output. Auto preserves the old default_output behavior. Changing devices or storage requires stopping the recorder. The real G733, audio routing and external disk still require target tests.

Settings now includes five dark presets and a saved custom palette (background, panels, borders and accent), a live swatch preview, and a scrollable settings page. Light background colors are restricted for readability. The overview, clips, editor, navigation and controls share the palette. No changes to Hyprland decorations.

Save changes replaces an MP4 at the same path after explicit confirmation, successful FFmpeg export, media probe and identity checks. It stages locally, copies to a hidden temporary file on the destination filesystem, then atomically renames over the original. The previous version is not kept after success. Failed/cancelled exports do not replace the original; completed exports that cannot be committed are retained in the local recovery folder. Non-MP4 files can be viewed, but in-place editing is MP4 only. Do not edit files while another app writes them. Music preview is still source-only. For tests run `python3 test_core.py` in the extracted directory (FFmpeg required). Tested with synthetic audio module lists, real FFmpeg trim and temporary local directories simulating storage failures; Qt rendering, real hardware, and external filesystem behavior not verified here.

## 0.6.2 — Playback polish

- Full screen in Clips and Editor, with playback, seek and Escape/F11 to exit. Reuses the existing media player and restores the inline preview.
- The F8 duration selector in the top bar is available on every page and shares the same configuration as the Replay duration buttons. No restart needed.
- Recorder, audio bridge, disk handling, clip export and themes unchanged from 0.6.

## 0.6.3

Top duration button uses a themed menu instead of the clipped Qt combo box. Custom durations from 2 seconds up to the configured replay buffer (default 1200 seconds) are accepted by both the CLI and F8 save path; no recorder restart needed for changing the save duration. Audio and storage implementations unchanged.


## 0.7 — Niri (experimental)

- Detects Niri and Hyprland from the session environment. Hyprland retains the previous capture target and bindings.
- On Niri, the default is GPU Screen Recorder's PipeWire portal (`-w portal`), with a monitor-sharing dialog at start and a longer startup grace period. Use a working `niri-session` and the GNOME screencast portal. The portal must be authorized by the user. If direct capture is supported on your hardware, stop replay and run `lolreplay niri-capture screen` to select the first monitor instead; `lolreplay niri-capture portal` restores the default. No automatic fallback or permission changes.
- `lolreplay niri-bind` is opt-in from a Niri session; it validates the existing and candidate KDL with the installed `niri` binary, retains a timestamped backup, and refuses ambiguous configs or detected F8 conflicts. If it refuses a config with includes or unusual formatting, run `lolreplay niri-bind-print` and insert the printed line into the existing active `binds {}` section; then run `niri validate`. Do not create a second binds block. For nonstandard config paths, `lolreplay niri-bind --config /path/to/config.kdl`.
- `lolreplay doctor` reports compositor and backend. Settings includes the same info and Niri setup controls. Existing audio, storage, editor and themes are unchanged. Fresh installation no longer needs a prior Crimson Clips installation; the listed dependencies must already be installed.
- Regression tests: `python3 -m unittest -v test_core test_compositor`. Actual compositor, portal, GPU, shortcut and audio behavior must still be validated in real Niri and Hyprland sessions.
- Reference: https://niri-wm.github.io/niri/Screencasting.html ; https://niri-wm.github.io/niri/Configuration%3A-Key-Bindings.html ; https://man.archlinux.org/man/extra/gpu-screen-recorder/gpu-screen-recorder.1.en

## 0.8 — Performance
- Background UI polling and new thumbnail jobs pause when the application is inactive or minimized. Capture, F8 and running exports continue independently. Refresh resumes on focus. An existing thumbnail job may finish.
- Thumbnail decoding/filtering/encoding use one FFmpeg thread each and nice +10 when available.
- Settings → Performance: Light 30 FPS/6 Mbps, Balanced 60 FPS/12 Mbps, High 60 FPS/20 Mbps. Existing settings are retained; quality changes require stopping replay.
- Replay history can be set to 30–1200 seconds. The selected F8 length is clamped if needed. The displayed MB is an estimate of video payload, not measured RAM.
- CLI: `lolreplay profile light|balanced|high`, `lolreplay buffer 300`.
- Niri remains experimental; real compositor and game performance measurements pending.

## 0.9 — Stability

- Recorder status: 0 running, 1 stopped (gsr-cli reports not running), 2 unknown/error. IPC requests have bounded timeouts. Concurrent engine commands wait at most five seconds for the lock.
- Invalid configuration is reported without overwriting the file. Status and Stop no longer depend on readable settings. The UI blocks configuration changes until repaired.
- Startup failure stops the spawned recorder and cleans up the isolated audio bridge. Stop waits for the recorder to confirm shutdown before releasing audio. Malformed audio state is reported without unloading unrelated modules.
- Storage copies verify that the source did not change. Failed transfers retain the local recovery file. Completed exports are retained locally if committing them fails.
- Installer checks dependencies and refuses to install while another engine operation holds the lock. Existing per-file backups remain available.

### Tests

Run `python3 -m unittest discover -v` in the source directory. The tests require FFmpeg and FFprobe, and use temporary directories and mocked recorder/audio operations. They do not require PySide6 or live capture hardware.

### Manual release checklist (not covered by automated tests)

1. Hyprland: start/stop repeatedly, save with F8 while playing, verify system audio and G733 microphone with no OSD.
2. Change recording duration and capture quality; confirm settings persist after relaunch.
3. Verify that the recorder continues when the GUI is closed. Check that F8 works when GUI is inactive.
4. External disk: stop before unplugging in normal use. To test the absent-disk recovery path safely, use a disposable test library and no important data. Recovery files live in `~/.local/state/crimson-clips/recovery`; access through Settings > Recovery folder. Nothing is automatically deleted there.
5. Edit a disposable clip, cancel an export, then save changes; confirm the original is replaced only after successful export.
6. Test fullscreen, all themes and small windows. Check playback and thumbnail updates.
7. Niri: portal permission, capture, audio, F8 and shutdown. Experimental until validated on an actual Niri session.

No claim of full crash-proof operation or physical-disk durability under sudden power loss is made.


## 0.9.1 — Interface refinement

- Media-first visual hierarchy, flatter surfaces, compact playback actions, original line icons and an off-centre branded empty state. No added runtime dependencies beyond existing PySide6.
- Settings organized into Appearance, Capture & storage and System tabs. All previous controls remain accessible.
- Refined trim timeline with tick marks and a visible playhead; editing and export semantics are unchanged.
- Existing theme preferences, recorder, audio, storage, compositor and FFmpeg export code are retained. No continuous decorative animations.
- The existing icon is retained for local testing; do not distribute it publicly until FreeBSD trademark/logo permissions have been checked or a distinct replacement chosen.
- GUI and compositor testing remain manual; this release is not a public 1.0.


## 0.9.2 — Replay workspace and portability

- The Replay artwork uses the actual capture status, palette and selected duration. No decorative animation or additional background jobs. The small history ruler represents configured lengths, not measured buffered footage. Collection size is calculated from the existing library scan.
- Run `python3 install.py --check` for a read-only prerequisite report. This is not a certification of GPU or compositor compatibility.
- Arch Linux has user testing; other distributions are unverified. Niri is experimental. Ubuntu is not an official support target. The installer uses Python and per-user paths, not a package manager. Install a compatible native GPU Screen Recorder with `gsr-cli`, FFmpeg/FFprobe (including libx264 and AAC for editing), Python 3.10+, PySide6 with Qt Multimedia and a working Wayland platform plugin, PipeWire with PulseAudio compatibility (`pactl`), and optional UDisks2/lsblk for drive discovery. Exact package names and versions vary by distribution. A Flatpak-only recorder is not automatically supported. NixOS may need packaging or a suitable environment.
- A fresh install does not set F8 automatically. On Hyprland, use an unused F8 key in your active compositor config to execute the absolute path to `~/.local/bin/lolreplay` followed by `save` (expand `~` to your home path). Lua-based config: `hl.bind("F8", hl.dsp.exec_cmd("/home/YOUR_USER/.local/bin/lolreplay save"))`. Legacy config: `bind = , F8, exec, /home/YOUR_USER/.local/bin/lolreplay save`. Use only the syntax for your installed Hyprland; do not overwrite an existing bind. On Niri use `lolreplay niri-bind`.
- The current artwork is for private testing only; clear rights or replace it before public distribution.


## 0.9.3 — Playback interactions

- Single-click a clip tile to start playback; click it again or click the video itself to pause/resume. Latest capture and recent clips also open with a single click. Without integrated multimedia, the library retains double-click to open externally.
- Click-to-toggle is shared by the library, editor and fullscreen playback surfaces. The editor continues to play the selected trim range and ignores clicks while exporting.
- The current FreeBSD-derived icon is retained for local testing, not cleared for public distribution. The Foundation's trademark terms prohibit modifications and incorporation into other logos under standard permissions: https://freebsdfoundation.org/legal/trademark-usage-terms-and-conditions/ . Obtain explicit written permission for the exact design or replace it before public release. The software license does not grant rights to this artwork.
- Manual GUI check: click each preview twice, switch clips, test fullscreen, and verify export in progress cannot resume editor playback.
