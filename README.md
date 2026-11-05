# ToonSim for Home Assistant OS

A Home Assistant App wrapper for [ToonSoftwareCollective/toonsim](https://github.com/ToonSoftwareCollective/toonsim).

**Version 0.1.1:** the container base image is now Debian Trixie, which provides Python 3.13. This is required because ToonSim’s firmware extraction uses the `tarfile` `filter="data"` argument, which is not available in Python 3.11.

It builds ToonSim inside the app image for `aarch64` and `amd64`, runs the Qt interface on a virtual X display, and provides:

- The simulated Toon screen through Home Assistant Ingress (noVNC).
- Toon Mobile through the app's HTTP port (`8888`).
- Persistent simulator data and firmware under the app's `/data` directory.

> Experimental first version. The image is built locally by Home Assistant from the Dockerfile (Debian Trixie / Python 3.13). On a Raspberry Pi 4 this means the first installation compiles ToonSim on the Pi and can take some time. This repository has not yet been verified on physical Home Assistant hardware.

## Add this repository to Home Assistant

1. Create a new **public GitHub repository** and upload the contents of this folder to its root.
2. Edit `repository.yaml`: replace the URL and maintainer with your own details.
3. In Home Assistant, open **Settings → Apps → Install app → ⋮ → Repositories**.
4. Add the URL of your new GitHub repository.
5. Install **ToonSim**.

The app is listed as experimental until the first successful build and runtime test.

## Initial configuration

Open the app's Configuration tab and enter the IP address, SSH username and SSH password of your rooted Toon. The app copies the required GUI resources from the Toon over SSH. The copy operation only reads from the physical Toon; it does not install anything or change its settings.

The firmware is stored locally in the app's persistent data directory and is not part of this Git repository or the Docker image. Do not publish or share the `firmware` directory: it contains Eneco/Quby firmware resources intended to remain with the owner of the Toon.

After the initial copy, the simulator starts automatically. Use **Open Web UI** in Home Assistant to open the simulated touchscreen. Toon Mobile is available at `http://HOME_ASSISTANT_IP:8888/mobile/`.

## Notes

- The app supports Home Assistant OS on `aarch64` (including Raspberry Pi 4 64-bit) and `amd64`.
- It does not require host networking, USB access, privileged mode, or the Docker API.
- Port `8888` serves Toon Mobile without its own login. Keep it on your trusted LAN; do not forward it to the internet. You can disable the port mapping in the app's Network settings if you only need the Ingress touchscreen.
- The touchscreen is exposed through Home Assistant Ingress, so access is protected by Home Assistant authentication.
- If you select `auto` for the model, ToonSim uses the model discovered from the physical Toon firmware. You can override it with Toon 1 or Toon 2.
- The source code is fetched from the upstream repository's `main` branch when the app image is built. Review upstream changes before rebuilding if you need a pinned/reproducible source revision.

## Upstream project and licensing

ToonSim is developed by ToonSoftwareCollective / ToonzDev. This wrapper does not replace or claim ownership of ToonSim. See the upstream repository for its MIT license and source history.

The Toon firmware is proprietary firmware from Eneco/Quby and is **not** included. The simulator requires the owner to retrieve it from their own rooted Toon.
