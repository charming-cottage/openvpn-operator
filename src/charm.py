#!/usr/bin/env python3
# Copyright 2024 Alex Lowe
# See LICENSE file for licensing details.
#
# Learn more at: https://juju.is/docs/sdk

import logging
import pathlib
import subprocess

import ops

# Log messages can be retrieved using juju debug-log
logger = logging.getLogger(__name__)

CONFIG_PATH = pathlib.Path("/etc/openvpn/openvpn.conf")
CREDS_PATH = pathlib.Path("/etc/openvpn/creds.txt")


class OpenvpnOperatorCharm(ops.CharmBase):
    """Charm the service."""

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.install, self._on_install)
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.start, self._on_start)
        self.framework.observe(self.on.stop, self._on_stop)

    def _on_install(self, event: ops.InstallEvent):
        """Install OpenVPN, etc."""
        self.unit.status = ops.MaintenanceStatus("installing OpenVPN")
        subprocess.run(
            ["apt-get", "update"],
            check=True
        )
        apt = subprocess.Popen(
            ["apt-get", "--yes", "install", "openvpn"],
        )
        CONFIG_PATH.parent.mkdir(exist_ok=True)
        CONFIG_PATH.write_text(self.config["config"])
        apt.wait()

    def _on_start(self, event: ops.EventBase):
        self.unit.status = ops.MaintenanceStatus("starting")
        subprocess.run(
            ["systemctl", "start", "openvpn"],
            check=True
        )
        self.unit.status = ops.ActiveStatus("openvpn connected")

    def _on_stop(self, event: ops.EventBase):
        self.unit.status = ops.MaintenanceStatus("stopping")
        subprocess.run(["systemctl", "stop", "openvpn"], check=True)
        self.unit.status = ops.MaintenanceStatus("stopped")

    def _on_config_changed(self, event: ops.ConfigChangedEvent):
        self.unit.status = ops.MaintenanceStatus("updating configuration")
        with CONFIG_PATH.open("wt") as ovpn_file:
            ovpn_file.write(self.config["config"])
            if self.config["username"]:
                ovpn_file.write("\nauth-user-pass /etc/openvpn/creds.txt\n")

        if self.config["username"]:
            with CREDS_PATH.open("wt") as creds_file:
                creds_file.writelines([self.config["username"], "\n", self.config["password"]])
        subprocess.run(["systemctl", "reload-or-restart", "openvpn"])


if __name__ == "__main__":  # pragma: nocover
    ops.main(OpenvpnOperatorCharm)  # type: ignore
