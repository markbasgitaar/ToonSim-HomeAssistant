# ToonSim for Home Assistant OS

Home Assistant App wrapper for [ToonSoftwareCollective/toonsim](https://github.com/ToonSoftwareCollective/toonsim).

## What changed in 0.2.0

- GitHub Actions builds separate native ARM64 and AMD64 images and publishes one multi-architecture image to GitHub Container Registry (GHCR).
- Home Assistant downloads the prebuilt image. The Raspberry Pi does **not** compile ToonSim during installation or app updates.
- Toon firmware remains in the app's persistent `/data` directory. Two compressed firmware snapshots are retained automatically (latest and previous).
- If firmware is absent, incomplete, or a fresh copy fails, the app attempts to restore a valid saved snapshot before failing.
- A manual recovery switch is available in Configuration: enable **Restore firmware backup**, restart the app, and turn the switch off again after recovery.
- Logs include UTC timestamps, startup stages, architecture, resolution, backup/restore events, and full exception details. Passwords are not printed.
- The original Toon screen sizes are preserved: Toon 1 is **800×480**, Toon 2 is **1024×600**.
- All app options have defaults and non-optional schema entries, so Home Assistant displays them directly in Configuration rather than hiding them behind the optional-options expander.

## GitHub Container Registry setup

1. Push this repository to `https://github.com/markbasgitaar/ToonSim-HomeAssistant` on the `main` branch.
2. Open **Actions** in GitHub and confirm that **Build and publish ToonSim images** completes for both `aarch64` and `amd64`.
3. Open the repository's **Packages** section (or the `toonsim-homeassistant` package under your GitHub profile), open **Package settings**, and set package visibility to **Public**. Home Assistant must be able to pull the image without GitHub credentials.
4. The workflow publishes `latest`, the app version from `toonsim/config.yaml`, and architecture-specific build tags.
5. Whenever you change the app code, increment `version` in `toonsim/config.yaml` and push to `main`. Home Assistant detects the version change; the workflow creates the matching image tags.

The workflow uses GitHub-hosted native ARM64 (`ubuntu-24.04-arm`) and AMD64 (`ubuntu-24.04`) runners. Compilation takes place in GitHub Actions, not on the Raspberry Pi.

## Add this repository to Home Assistant

1. Open **Settings → Apps → Install app → ⋮ → Repositories**.
2. Add `https://github.com/markbasgitaar/ToonSim-HomeAssistant`.
3. Install **ToonSim** after the GitHub Actions build has completed and the GHCR package is public.

## Initial configuration

All settings are shown directly in the Configuration page:

- **Toon IP**: IP address of the rooted physical Toon.
- **Toon username**: normally `root`.
- **Toon password**: SSH password for the rooted Toon.
- **Copy apps**: optionally copy custom apps from the physical Toon.
- **Copy settings**: optionally copy readable app settings.
- **Model**: `auto`, `toon1`, or `toon2`. Auto-detect uses the model marker copied from the physical Toon.
- **Restore firmware backup**: manual recovery switch. Turn it on, restart the app, then turn it off again after the recovery is complete.

The firmware pull reads from the physical Toon over SSH. It does not install anything on the Toon or change its settings. The password is not written to the app log.

## Backups and recovery

The app stores its working firmware under `/data/toonsim/firmware` and compressed snapshots under `/data/toonsim/backups/`. These paths are persistent across app-image updates. The latest and previous snapshots are kept; they are not included in this Git repository or Docker image.

If the active firmware becomes incomplete, the app tries the latest backup and then the previous backup. If a normal app update itself fails before the container can start, use Home Assistant's own app/HA backup restore mechanism; code inside a container cannot roll back a container image that never starts. The firmware recovery switch is for restoring the saved firmware files after the app can start again.

For extra protection, create a Home Assistant backup before a major app update. This backup includes the app's persistent data when the app is included in the backup.

## Networking and security

- The simulated touchscreen is served through authenticated Home Assistant Ingress.
- Port `8888` serves Toon Mobile without built-in authentication. Keep it on a trusted LAN and do not forward it to the internet. You can disable the port mapping in the app's Network settings if you only use the touchscreen.
- The container does not need host networking, USB access, privileged mode, or Docker socket access.
- Firmware belongs to the owner of the physical Toon. Do not publish or share the `firmware` or `backups` directories.

## Upstream project and licensing

ToonSim is developed by ToonSoftwareCollective / ToonzDev. This wrapper does not replace or claim ownership of ToonSim. See the upstream project for its license and source history. The Toon firmware is proprietary firmware from Eneco/Quby and is not included in this repository or in the container image.
