# lolreplay 1.7.0 — AUR packaging candidate

This branch holds a package recipe, not a published AUR package. It uses the tested upstream baseline at commit `8a1627e0831bbf52c1aaef9e8cdd562b0ada86f4`, not a moving branch. The Git source is pinned to an immutable commit; SKIP applies to the VCS source checksum. No changes to main are required. Only x86_64 is declared pending other architecture testing.

## Build and review on Arch (as an ordinary user)

```sh
sudo pacman -S --needed base-devel git namcap
cd packaging/aur
makepkg --printsrcinfo > .SRCINFO
makepkg -s
namcap PKGBUILD
namcap lolreplay-1.7.0-1-x86_64.pkg.tar.zst
```

Use the actual filename printed by makepkg if your package extension differs. Do not publish until build, lint review, and a real package install pass. Check that gsr-cli is present in the installed recorder package. The build check covers Python syntax, Qt imports, version and updater guard; it is not a full desktop test.

Test preferably in a clean Arch VM or a separate clean user profile. Install the built package with `sudo pacman -U ./lolreplay-1.7.0-1-x86_64.pkg.tar.zst` and run `/usr/bin/lolreplay --version`, `/usr/bin/lolreplay doctor`, and `/usr/bin/lolreplay`. Start/save/stop, play/edit, test automatic game detection, and verify the Settings Updates page explains package-managed updates. Set the global shortcut to `/usr/bin/lolreplay save` using the compositor's native configuration. Verify package ownership with `pacman -Ql lolreplay`; remove the test package with `sudo pacman -R lolreplay` if desired. Existing user clips/configuration are not removed by pacman.

Existing manual installations may shadow /usr/bin through ~/.local/bin, and a local desktop entry or existing F8 binding may still select the manual copy. Stop capture and exit the UI before switching. Do not delete any config or videos; inspect and back up the exact manual launcher/desktop files before migrating. Until migration is tested, use the absolute /usr/bin path and keep the current working manual installation.

## Publish when AUR registration reopens

1. Create your account with parent/guardian permission if required; register only your SSH public key. Verify the server fingerprint against the official AUR submission guidelines. No automated registration retries.
2. Check that the package name is available via the AUR website. If another maintainer owns it, do not overwrite or claim their package.
3. Clone the AUR package repository with your own SSH key; copy only the reviewed PKGBUILD and regenerate .SRCINFO. Configure public Git author metadata locally.
4. Commit PKGBUILD and .SRCINFO, then push. Do not commit source downloads, build directories, private keys or binary packages.
5. Once AUR shows the package, test installation with yay -S lolreplay from a clean environment.

For future versions, update the pinned upstream commit, pkgver/pkgrel and metadata, rebuild, review and regenerate .SRCINFO. The AUR package uses the package manager rather than lolreplay's standalone updater.
