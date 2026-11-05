# ToonSim – Home Assistant App 0.2.1

This app runs the upstream ToonSim project inside a container on Home Assistant OS.

## Requirements

- Home Assistant OS with Supervisor / Apps support.
- A 64-bit installation (`aarch64`) on a Raspberry Pi 4, or `amd64`.
- A rooted Toon 1 or Toon 2 reachable over your LAN using SSH.
- Internet access for the first firmware pull and any upstream components that require it.
- A publicly accessible GHCR image for the configured version.

## First start

1. Install the app and open its **Configuration** tab.
2. Set `toon_ip` to the LAN IP of your rooted Toon.
3. Set `toon_username` (normally `root`) and enter the SSH password in `toon_password`.
4. Leave `model` on `auto` unless you want to override the detected model.
5. Save and start/restart the app.

On first start, the app copies Toon GUI resources from the device using SSH. The copy tool reads from the Toon; it does not write to it. Keep the Toon powered on and reachable. The password is not written to normal app logs.

## Display and access

- Toon 1 uses **800×480**.
- Toon 2 uses **1024×600**.
- Touchscreen: open the app's Web UI / sidebar entry. Home Assistant Ingress authenticates access.
- Toon Mobile: `http://<Home Assistant IP>:8888/mobile/` from your LAN.

Port 8888 has no independent login. Do not expose it to the internet or configure router port forwarding. Disable the port mapping if you do not need direct LAN access.

## Persistent firmware and recovery

Firmware and simulator state live under `/data/toonsim/`. Firmware snapshots are saved under `/data/toonsim/backups/`; the latest and previous known-good snapshots are retained.

If active firmware is missing or invalid, the app tries to restore a backup before attempting a new SSH copy. To request a manual restore, enable **Restore firmware backup**, restart the app, and then disable the option again after recovery.

These backups are local to the Home Assistant app data and are not included in this source archive or the container image. Create a Home Assistant backup before major app updates.

If the container image cannot be downloaded or the container cannot start, restore the Home Assistant app/system backup; firmware recovery code cannot run before the container starts.

## Configuration options

| Option | Description |
|---|---|
| `toon_ip` | IP address of the rooted Toon. Required for initial firmware copy. |
| `toon_username` | SSH username; normally `root`. |
| `toon_password` | SSH password. Required for initial firmware copy unless firmware is already stored or a backup exists. |
| `copy_apps` | Also copy custom apps from the physical Toon on first setup. |
| `copy_settings` | Also copy readable TSC app settings on first setup. |
| `model` | `auto`, `toon1` or `toon2`. Auto uses the model marker from copied firmware. |
| `restore_firmware_backup` | Restore the latest valid firmware snapshot on next start. |

## Troubleshooting

- **Image pull denied:** verify the GHCR package `toonsim-homeassistant` exists, the requested tag is published, and package visibility is Public.
- **Firmware copy fails:** confirm IP, SSH username/password, SSH access, and network reachability. Check the app log for the underlying SSH error.
- **Touchscreen does not load:** check app logs for Qt/QML errors. The Ingress listener is restricted to the Supervisor ingress gateway address.
- **Toon Mobile does not load:** verify port 8888 is enabled and use the Home Assistant IP address.
- **No firmware or backup found:** configure `toon_ip` and `toon_password`, save, and restart.

## Firmware and copyright

ToonSim does not include Toon firmware. Firmware resources are retrieved from the user's own rooted Toon and remain in that user's Home Assistant app data. Do not upload or share the firmware directory or its backups.

ToonSim is not affiliated with Eneco or Quby. See the upstream project's repository and license for its code licensing terms.
