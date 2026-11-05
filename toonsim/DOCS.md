# ToonSim – Home Assistant App 0.2.3

This app runs the upstream ToonSim project inside a container on Home Assistant OS.

## Requirements

- Home Assistant OS with Supervisor / Apps support.
- A 64-bit installation (`aarch64`) on a Raspberry Pi 4, or `amd64`.
- A rooted Toon 1 or Toon 2 reachable over your LAN using SSH.
- Internet access for the first firmware pull and any upstream components that require it.
- A publicly accessible GHCR image for the configured version.
- Optional: the Samba NAS app (or another SMB server) to edit custom apps from your PC.

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

### Display scaling

The noVNC touchscreen uses **Local scaling (shrink only)**:

- On a browser viewport smaller than the Toon resolution, the screen is scaled
  down so it still fits.
- On a larger viewport, the screen stays at its real 1:1 resolution and is
  centred. It is never enlarged, so Toon 1 remains 800×480 and Toon 2 remains
  1024×600 on screen.

You can still choose **None** manually in noVNC's settings panel, and that
choice is remembered. The **Local scaling** option is the shrink-only variant
described above; the app selects it as the initial setting through noVNC's
`defaults.json`.

Port 8888 has no independent login. Do not expose it to the internet or configure router port forwarding. Disable the port mapping if you do not need direct LAN access.

## Custom apps via SMB

ToonSim's custom apps live in `/share/ToonSim/apps`. Home Assistant's `/share`
folder is exposed by Samba NAS as the **share** SMB share, so from your PC open:

```
\\<Home Assistant IP>\share\ToonSim\apps
```

On Linux or macOS use `smb://<Home Assistant IP>/share/ToonSim/apps`. Make sure
the **share** share is enabled in Samba NAS; no extra Samba configuration is
needed. `ToonSim` appears as a folder inside the existing `share` share.

The folder is created automatically. Each app goes in its own folder, just like
`/qmf/qml/apps` on a real Toon:

```
\\<Home Assistant IP>\share\ToonSim\apps\myapp\MyappApp.qml
```

After adding or changing an app, restart the ToonSim app. The simulator loads
the apps folder at startup, like the Toon itself.

Existing apps from earlier versions are copied once from
`/data/toonsim/apps` on the first start after upgrading. If neither location has
apps yet, the bundled ToonStore is placed there. The old `/data/toonsim/apps`
folder is left untouched as a backup. Apps in `/share` survive app updates and
reinstallations.

Only place apps you trust in this folder: app scripts run inside the ToonSim
container.

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
- **No `ToonSim` folder over SMB:** enable the **share** share in Samba NAS and start ToonSim once; the app creates `/share/ToonSim/apps` at startup. Check the app log for the `Apps folder:` line.
- **New app does not appear:** restart the ToonSim app; apps are loaded at startup.
- **No firmware or backup found:** configure `toon_ip` and `toon_password`, save, and restart.

## Firmware and copyright

ToonSim does not include Toon firmware. Firmware resources are retrieved from the user's own rooted Toon and remain in that user's Home Assistant app data. Do not upload or share the firmware directory or its backups.

ToonSim is not affiliated with Eneco or Quby. See the upstream project's repository and license for its code licensing terms.
