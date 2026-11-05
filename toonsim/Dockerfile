# Built by GitHub Actions for ARM64 and AMD64. HA pulls the finished image from GHCR.
FROM debian:trixie-slim

ARG BUILD_VERSION
ARG BUILD_ARCH
ARG TOONSIM_REF=main
ARG BUILD_JOBS=2

LABEL \
  io.hass.name="ToonSim" \
  io.hass.description="Toon thermostat simulator" \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}" \
  org.opencontainers.image.source="https://github.com/markbasgitaar/ToonSim-HomeAssistant"

ENV DEBIAN_FRONTEND=noninteractive \
    QT_X11_NO_MITSHM=1 \
    QT_QUICK_BACKEND=software \
    QT_OPENGL=software \
    LIBGL_ALWAYS_SOFTWARE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates git build-essential \
      qtbase5-dev qtbase5-dev-tools qtdeclarative5-dev libqt5svg5-dev \
      qml-module-qtquick2 \
      qml-module-qtquick-window2 \
      qml-module-qtquick-controls \
      qml-module-qtquick-controls2 \
      qml-module-qtquick-templates2 \
      qml-module-qtquick-layouts \
      qml-module-qtgraphicaleffects \
      qml-module-qtquick-xmllistmodel \
      qml-module-qtquick-localstorage \
      qml-module-qtquick-particles2 \
      qml-module-qtquick-shapes \
      qml-module-qtqml-models2 \
      qml-module-qt-labs-folderlistmodel \
      qml-module-qt-labs-settings \
      qml-module-qtwebsockets \
      qml-module-qtquick-dialogs \
      qtvirtualkeyboard-plugin \
      qml-module-qtquick-virtualkeyboard \
      libqt5svg5 \
      python3 openssh-client \
      xvfb x11vnc novnc websockify nginx-light \
      libxcb-xinerama0 libxcb-cursor0 libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*

# Compilation takes place on the matching native GitHub Actions runner.
RUN git clone --depth 1 --branch "${TOONSIM_REF}" \
      https://github.com/ToonSoftwareCollective/toonsim.git /opt/toonsim \
    && mkdir -p /opt/toonsim/src/build-linux \
    && cd /opt/toonsim/src/build-linux \
    && qmake ../toonsim.pro CONFIG+=release \
    && make -j"${BUILD_JOBS}" \
    && test -x /opt/toonsim/bin/toonsim \
    && test -f /opt/toonsim/toonsim.sh \
    && rm -rf /opt/toonsim/.git /opt/toonsim/src/build-linux

COPY run.sh /run.sh
COPY entrypoint.py /opt/ha-toonsim/entrypoint.py
COPY nginx.conf /etc/nginx/conf.d/toonsim.conf

RUN chmod 0755 /run.sh /opt/toonsim/toonsim.sh \
    && rm -f /etc/nginx/sites-enabled/default \
    && mkdir -p /data/toonsim /run/nginx /opt/ha-toonsim

WORKDIR /opt/toonsim
CMD ["/run.sh"]
