# ToonSim – Home Assistant App

This app runs the upstream ToonSim project inside a container on Home Assistant OS.
It is an **experimental first release** and has not yet been validated on a physical Raspberry Pi 4.

## Requirements

- Home Assistant OS with Supervisor / Apps support.
- A 64-bit installation (`aarch64`) on a Raspberry Pi 4, or `amd64`.
- A rooted Toon 1 or Toon 2 reachable over your LAN using SSH.
- Internet access from the app container for the first ToonSim start (ToonSim installs its helper/mobile components from upstream sources).

## First start

1. Install the app and open its **Configuration** tab.
2. Set `toon_ip` to the LAN IP address of your rooted Toon.
3. Set `toon_username` (normally `root`) and enter the Toon SSH password in `toon_password`.
4. Leave `model` on `auto` unless you want to override the detected Toon model.
5. Save and start/restart the app.

On its first start, the app copies the Toon GUI resources from the device using SSH. The upstream copy tool reads from the Toon; it does not write to it. Keep the Toon powered on and reachable during this operation. The password field is a Home Assistant secret/password option and is not written into the app's normal log output.

The copied GUI resources are stored under the app's persistent `/data/toonsim/firmware` directory. The app also stores apps, settings and simulator state there. They survive app restarts and updates.

## Open ToonSim

- **Touchscreen:** open the app's **Open Web UI** button or its Home Assistant sidebar entry. It uses Home Assistant Ingress authentication.
- **Toon Mobile:** open `http://<Home Assistant IP>:8888/mobile/` from your LAN.

Toon Mobile uses port 8888, which has no independent login. Do not expose this port to the internet or configure router port forwarding. Disable its port mapping in the app's Network settings if you do not need direct LAN access.

The embedded ToonSim HTTP server listens only on loopback inside the container. Nginx proxies it to the app's LAN port. The virtual touchscreen uses Xvfb, x11vnc and noVNC; the VNC server itself listens only on loopback and the Ingress listener accepts only the Supervisor ingress gateway address.

## Configuration

| Option | Description |
|---|---|
| `toon_ip` | IP address of the rooted Toon. Required for initial firmware copy. |
| `toon_username` | SSH username; normally `root`. |
| `toon_password` | SSH password. Required for initial firmware copy unless firmware was copied previously. |
| `copy_apps` | Also copy custom apps from the physical Toon on first setup. |
| `copy_settings` | Also copy TSC app settings on first setup. |
| `model` | `auto`, `toon1` or `toon2`. Auto uses the model reported by the copied firmware. |

## Updating firmware from the physical Toon

This first version only copies firmware automatically when no firmware is stored yet. It does not overwrite existing firmware during a normal restart. To force a fresh copy, use the app's persistent storage and remove the contents of `/data/toonsim/firmware` while the app is stopped, then set the SSH details and start the app again. Keep a backup before doing this.

## Troubleshooting

- **Firmware copy fails:** confirm the IP, SSH username/password, that SSH is enabled on the rooted Toon, and that the Toon and Home Assistant are on mutually reachable networks. Check the app log for the SSH error.
- **Touchscreen does not load:** check the app log for Qt/QML errors. The Ingress listener is intentionally restricted to `172.30.32.2` as required for Home Assistant Ingress.
- **Toon Mobile does not load:** verify that port 8888 is enabled in the app's Network settings and that the URL uses the Home Assistant IP.
- **No firmware found:** configure `toon_ip` and `toon_password`, save, and restart.

## Firmware and copyright

ToonSim does not include Toon firmware. The firmware resources are retrieved from the user's own rooted Toon and remain in that user's Home Assistant app data. Do not upload the firmware directory to GitHub, share it, or include it in backups supplied to other people.

ToonSim is not affiliated with Eneco or Quby. See the upstream project's repository and MIT license for its code licensing terms.
