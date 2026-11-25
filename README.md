<p align="center">
  <img src="lolreplay.png" alt="lolreplay emblem" width="120">
</p>

<h1 align="center">lolreplay</h1>
<p align="center"><strong>No cloud. Just clips.</strong></p>
<p align="center">Local instant replay for Linux / Wayland · v1.0.0 · MIT-licensed software</p>

lolreplay is a free, open-source desktop application for saving the moments that matter while gaming on Linux. It uses GPU Screen Recorder for capture and FFmpeg for local editing. No accounts, ads, uploads, subscriptions or watermarks. Your recordings stay on your machine.

## Features

- GPU-assisted instant replay, adjustable quality, history and clip duration.
- Global capture shortcut (F8 by default), configurable internal shortcuts and keyboard navigation.
- Local clip library with thumbnails, search, sorting, fullscreen playback and an integrated editor.
- Trim recordings, adjust audio and add local music; save edits directly to the library.
- Microphone and capture-output selection, external storage and local recovery on transfer failure.
- Dark themes, custom colours, accessibility preferences and nine interface languages.
- Reduced background polling and thumbnail work when the app is unfocused by default.

## Compatibility

| Environment | Status |
| --- | --- |
| Arch Linux + Hyprland | Tested by the project maintainer during development |
| Niri | Experimental; live capture and global shortcuts not yet verified |
| Other Linux distributions | May work if prerequisites are available; unverified |
| Ubuntu | Not an official support target |
| X11 / other Wayland compositors | Not supported targets |

Requirements: Linux, Python 3.10+, native GPU Screen Recorder **with `gsr-cli`**, FFmpeg and FFprobe (libx264 and AAC for editing), PySide6 with Qt Multimedia and Wayland support, and PipeWire with PulseAudio compatibility (`pactl`). Optional: `lsblk`, UDisks2 (`udisksctl`), `notify-send`. GPU support depends on the recorder and drivers. A Flatpak-only recorder is not automatically supported.

## Installation

Download the release ZIP and extract it, or clone this repository. On Arch, the Qt and FFmpeg dependencies can be installed with:

```sh
sudo pacman -S --needed pyside6 qt6-wayland qt6-multimedia qt6-multimedia-ffmpeg ffmpeg
```

Install GPU Screen Recorder and PipeWire prerequisites separately using your distribution's supported method. The recorder must provide both `gpu-screen-recorder` and `gsr-cli` on PATH.

From the extracted project directory:

```sh
python3 install.py --check
python3 install.py
~/.local/bin/lolreplay
```

The installer is per-user; do not run it with sudo. If `lolreplay` is not found, add `~/.local/bin` to your PATH, or use the full path. The prerequisite check cannot certify actual capture or GPU compatibility.

For updates, save any replay you want to keep, stop the recorder and close the UI before installing. Existing clips, settings and compositor bindings are preserved; changed files are backed up.

### Set up the capture hotkey

A fresh installation does not automatically claim a global key. In Hyprland, choose a free binding in your active configuration to execute the absolute path to `~/.local/bin/lolreplay` followed by `save`. For example, in a Lua configuration (replace the example path with your own):

```lua
hl.bind("F8", hl.dsp.exec_cmd("/home/your-user/.local/bin/lolreplay save"))
```

For legacy Hyprlang configuration, use its native syntax instead. For Niri, run `lolreplay niri-bind` for the initial default F8 binding. Check for conflicts first, reload your compositor and test capture. Settings → Keyboard shortcuts can change recognised managed bindings, or provide a snippet for manual setup. Backups are created for automatic changes. Do not run the initial F8 setup again after choosing a different global key.

## Everyday use

1. Start replay and choose a duration within the configured history.
2. Press your capture shortcut to save a clip.
3. Watch, rename or edit it directly from the local library.

Change quality, audio devices and storage while replay is stopped. Closing the UI does not stop the recorder. Esc always exits fullscreen. Editing uses a temporary export and confirmation before replacing the original; **there is no undo after successful replacement**. Preview plays original audio only; music is mixed during export. If an external drive fails, check the status for a recoverable local copy.

Settings includes appearance, language, capture, system, accessibility and keyboard shortcuts. English, Spanish (Spain), French, German, Russian, Polish, Japanese, Simplified Chinese and Italian are available. Reopen the UI to apply a language change. Technical logs and some platform dialogues may remain untranslated. Larger controls or longer translations may require a wider window. Screen-reader compatibility has not been validated.

### CLI and diagnostics

```sh
lolreplay --version
lolreplay doctor
lolreplay --help
lolreplay start
lolreplay status
lolreplay save 30
lolreplay stop
```

## Testing and reporting bugs

```sh
python3 -m unittest -v
```

Automated tests cover core logic, simulated failures, preferences, translations, shortcuts, installation and FFmpeg operations. They do not replace live testing of Qt, GPU capture, physical disks, microphones and Niri. Please report the distribution, compositor, GPU, version, reproduction steps and relevant redacted diagnostic output. Remove usernames, private paths and other personal information before posting logs.

See [CHANGELOG.md](CHANGELOG.md) for development history. Older instructions there are historical, not installation guidance.

## Credits and license

Project direction, feature decisions and live testing: lolreplay's creator and contributors. Implementation, documentation, translation drafts and automated tests were developed with assistance from ChatGPT (OpenAI). Translations have not all been reviewed by native speakers.

Thanks to the GPU Screen Recorder, FFmpeg, Qt/PySide6, PipeWire, Hyprland and Niri projects. These are separate 
dependencies with their own licenses and are not bundled here.

- Project creator, design direction and testing: repository owner.
- AI-assisted development: ChatGPT by OpenAI.

Built for the Linux gaming community.
The software is distributed under the [MIT License](LICENSE). The emblem is AI-generated for lolreplay, inspired by gaming visual aesthetics; it replaces the previous FreeBSD-derived artwork, which is not included. No affiliation with FreeBSD, ASUS ROG or the dependency projects is implied. No trademark clearance is claimed.
