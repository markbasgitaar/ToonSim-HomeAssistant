# ToonSim for Home Assistant OS

Home Assistant App wrapper for [ToonSoftwareCollective/toonsim](https://github.com/ToonSoftwareCollective/toonsim).

## Version 0.2.1

- GitHub Actions builds native ARM64 and AMD64 images and publishes multi-architecture tags to GitHub Container Registry (GHCR).
- Home Assistant downloads the prebuilt image; the Raspberry Pi does not compile ToonSim during installation or updates.
- Toon firmware is stored persistently under `/data/toonsim`. Two compressed firmware snapshots are retained automatically (latest and previous).
- If firmware is missing, incomplete, or a fresh copy fails, the app attempts to restore a valid saved snapshot.
- Manual recovery is available with the **Restore firmware backup** configuration option.
- Logs include UTC timestamps, startup stages, architecture, resolution, backup/restore events, and exception details. Passwords are not printed.
- Toon 1 resolution remains **800×480**; Toon 2 remains **1024×600**.
- All configuration options have defaults and schema entries, so they are shown directly in Home Assistant Configuration.

## GitHub Container Registry

1. Push this repository to `https://github.com/markbasgitaar/ToonSim-HomeAssistant` on `main`.
2. In GitHub Actions, verify that **Build and publish ToonSim images** completes for both `aarch64` and `amd64`.
3. In the repository's **Packages** section, open `toonsim-homeassistant` → **Package settings** and set visibility to **Public**. Home Assistant needs to pull the image without registry credentials.
4. The workflow publishes `latest`, the version from `toonsim/config.yaml`, and temporary architecture-specific build tags.
5. For future releases, increment `version` in `toonsim/config.yaml` and push to `main`.

The workflow uses native GitHub-hosted ARM64 (`ubuntu-24.04-arm`) and AMD64 (`ubuntu-24.04`) runners. Compilation happens in GitHub Actions, not on the Raspberry Pi.

## Add the repository to Home Assistant

1. Open **Settings → Apps → Install app → ⋮ → Repositories**.
2. Add `https://github.com/markbasgitaar/ToonSim-HomeAssistant`.
3. Install ToonSim after the workflow has completed and the GHCR package is public.

## Configuration

- **Toon IP**: IP address of the rooted physical Toon.
- **Toon username**: normally `root`.
- **Toon password**: SSH password for the rooted Toon.
- **Copy apps**: optionally copy custom apps from the physical Toon.
- **Copy settings**: optionally copy readable app settings.
- **Model**: `auto`, `toon1`, or `toon2`.
- **Restore firmware backup**: enable this and restart the app to restore the saved firmware. Turn it off again after recovery.

The firmware pull reads from the physical Toon over SSH. It does not install anything on the Toon or change its settings. The password is not written to the app log.

## Backups and recovery

Working firmware is stored in `/data/toonsim/firmware`; compressed snapshots are stored in `/data/toonsim/backups/`. The latest and previous snapshots are retained across app-image updates. Firmware and backups are deliberately not included in this source archive or Docker image.

If active firmware is invalid, the app tries the latest backup and then the previous backup. If an app image itself cannot be pulled or the container cannot start, use Home Assistant's own app/HA backup restore mechanism; code inside a container cannot roll back an image that never starts.

Create a Home Assistant backup before a major app update.

## Networking and security

- The touchscreen is served through authenticated Home Assistant Ingress.
- Port `8888` serves Toon Mobile without built-in authentication. Keep it on a trusted LAN and do not forward it to the internet. Disable the port mapping if you only use the touchscreen.
- The container does not need host networking, USB access, privileged mode, or Docker socket access.
- Do not publish or share your own Toon `firmware` or `backups` directories.

## Upstream project and licensing

ToonSim is developed by ToonSoftwareCollective / ToonzDev. This wrapper does not replace or claim ownership of ToonSim. See the upstream project for its license and source history. Toon firmware is proprietary Eneco/Quby firmware and is not included in this repository or Docker image.
