<p align="center">
  <img src="lolreplay.png" alt="lolreplay emblem" width="120">
</p>

<h1 align="center">lolreplay</h1>
<p align="center"><strong>No cloud. Just clips.</strong></p>
<p align="center">Local instant replay for Linux / Wayland · v1.2.0 · MIT-licensed software</p>

lolreplay is a free, open-source desktop application for saving the moments that matter while gaming on Linux. It uses GPU Screen Recorder for capture and FFmpeg for local editing. No accounts, ads, uploads, subscriptions or watermarks. Your recordings stay on your machine.

## Features

- GPU-assisted instant replay, adjustable quality, history and clip duration.
- Global capture shortcut (F8 by default), configurable internal shortcuts and keyboard navigation.
- Local clip library with thumbnails, search, sorting, fullscreen playback and an integrated editor. Click or drag on playback bars to seek directly.
- Responsive layouts with compact navigation and scrollable pages for smaller displays, plus categorized settings.
- Trim recordings, adjust audio and add local music; save edits directly to the library.
- Microphone and capture-output selection, external storage and local recovery on transfer failure.
- Dark themes, custom colours, accessibility preferences and nine interface languages.
- Reduced background polling and thumbnail work when the app is unfocused by default.

## Updates (manual, opt-in)

From 1.2.0, open **Settings → Updates**, click **Check for updates**, select an eligible version and read its release notes. Preview releases are hidden by default. Installation requires a separate confirmation; save any wanted replay and stop capture first. The application will ask you to reopen it after a successful update. No automatic network requests, accounts or automatic installs. The updater contacts the public GitHub release API only on request. Only newer official ZIP assets with a GitHub SHA-256 digest are eligible; missing or mismatched digests fail closed. This is an integrity check, not independent code signing. Installation runs without sudo, checks prerequisites and restores installer-owned files on caught installation errors. Power loss or forced termination cannot be guaranteed recoverable; existing per-file backups are retained.

CLI alternative: `lolreplay update` lists eligible newer releases. `lolreplay update vX.Y.Z` shows notes and asks for confirmation. Add `--experimental` to include previews. First install 1.2.0 manually if upgrading from an earlier version. Future releases must keep the `lolreplay-vX.Y.Z.zip` asset and `install.py --update --from-version` contract. No automatic downgrades.

## Compatibility

| Environment | Status |
| --- | --- |
| Arch Linux + Hyprland (AMD) | Live capture confirmed through v1.0.1; v1.1.0 UI awaiting live testing |
| Debian 13 + Hyprland (Intel) | Live capture and automatic CQP retry confirmed in v1.0.1; responsive UI and editor hotfix confirmed by maintainer on Debian; v1.0.4 library layout fix confirmed by maintainer; v1.1.0 UI awaiting live testing |
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

### Debian 13 (Trixie)

The maintainer tested Debian 13.7 with Hyprland, Intel VA-API, Qt 6.8.2 and GPU Screen Recorder 6.1.7 built from source. Install the runtime dependencies:

```sh
sudo apt update
sudo apt install git unzip python3 ffmpeg pipewire pipewire-pulse wireplumber pulseaudio-utils udisks2 libnotify-bin qt6-wayland python3-pyside6.qtwidgets python3-pyside6.qtmultimedia python3-pyside6.qtmultimediawidgets mesa-utils vainfo intel-media-va-driver
```

Use the native recorder (both CLI executables required). If building from upstream source, consult [GPU Screen Recorder](https://git.dec05eba.com/gpu-screen-recorder/about/) for its dependencies. The following build dependencies were used on the tested Debian system:

```sh
sudo apt install --no-remove build-essential meson ninja-build pkg-config libx11-dev libxcomposite-dev libxrandr-dev libxfixes-dev libxdamage-dev libwayland-dev libwayland-bin libva-dev libpulse-dev libdrm-dev libcap-dev libdbus-1-dev libvulkan-dev libglvnd-dev linux-libc-dev libavcodec-dev libavformat-dev libavutil-dev libswresample-dev libavfilter-dev libpipewire-0.3-dev libspa-0.2-dev
```

If PipeWire and Wayland are already installed from Trixie Backports, first install the matching development packages from the enabled backports repository, then retry the build dependency command. Do not downgrade or remove desktop packages to resolve a version conflict.

```sh
sudo apt install --no-remove -t trixie-backports libpipewire-0.3-dev libspa-0.2-dev libwayland-dev libwayland-bin
```

Build and install the tested recorder version (review upstream code before installing):

```sh
git clone --depth 1 --branch 6.1.7 https://repo.dec05eba.com/gpu-screen-recorder
cd gpu-screen-recorder
meson setup build --prefix=/usr/local --buildtype=release
meson compile -C build -j 2
sudo meson install -C build
command -v gpu-screen-recorder
command -v gsr-cli
vainfo
```

Run these build steps in order; stop if any fails. Then return to the lolreplay source directory and run the normal installer above. On Debian 13, FFmpeg 7 may warn about MP4 fragmentation; if clips stutter, consult upstream's FFmpeg guidance. Do not mix Debian unstable packages into stable just for this warning.

### Encoder compatibility

Settings → Capture & storage → Rate control offers Auto, CBR and CQP. Auto starts with CBR (the previous behavior) and retries once with CQP only if the current failed recorder explicitly reports unsupported CBR and supported CQP. CQP uses quality presets rather than fixed bitrate; replay size can vary considerably. A short buffer is recommended on low-memory machines. The start command reports the actual mode. Portal capture may require selecting the monitor again on retry.

```sh
lolreplay rate-control auto
# Or force CQP when needed (while stopped):
lolreplay rate-control cqp
```

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

For the release gate, run `python3 -m unittest -v test_responsive` with PySide6 installed. The Qt test uses temporary homes and exercises nine languages, accessibility scales, and window sizes. A skipped Qt test is not a pass. Test actual playback, editor, fullscreen, and capture on Wayland before marking a release stable.

Automated tests cover core logic, simulated failures, preferences, translations, shortcuts, installation and FFmpeg operations. They do not replace live testing of Qt, GPU capture, physical disks, microphones and Niri. Please report the distribution, compositor, GPU, version, reproduction steps and relevant redacted diagnostic output. Remove usernames, private paths and other personal information before posting logs.

See [CHANGELOG.md](CHANGELOG.md) for development history. Older instructions there are historical, not installation guidance.

## Credits and license

Project direction, feature decisions and live testing: lolreplay's creator and contributors. Implementation, documentation, translation drafts and automated tests were developed with assistance from ChatGPT (OpenAI). Translations have not all been reviewed by native speakers.

Thanks to the GPU Screen Recorder, FFmpeg, Qt/PySide6, PipeWire, Hyprland and Niri projects. These are separate dependencies with their own licenses and are not bundled here.

The software is distributed under the [MIT License](LICENSE). The emblem is AI-generated for lolreplay, inspired by gaming visual aesthetics; it replaces the previous FreeBSD-derived artwork, which is not included. No affiliation with FreeBSD, ASUS ROG or the dependency projects is implied. No trademark clearance is claimed.
