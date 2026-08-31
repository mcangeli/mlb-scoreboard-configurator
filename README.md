# MLB LED Scoreboard Configurator — V3.0.0

A Bullpen-compatible Flask web configurator for
[MLB-LED-Scoreboard](https://github.com/MLB-LED-Scoreboard/mlb-led-scoreboard),
targeting the v9 configuration model.

## Version Highlights

### V3.0.0

- **Plugin management page** — A new **Plugins** page is available under the **System** heading in the web configurator.
- **Install plugins from GitHub** — Paste a direct GitHub repository URL and install the plugin without using SSH or manually running pip commands.
- **Uses the scoreboard virtual environment** — Plugin installation runs through the MLB-LED-Scoreboard `venv/bin/pip`, keeping plugins in the same Python environment as the scoreboard.
- **Installed plugin list** — Displays Bullpen plugins registered under `bullpen.mlbled.plugin`, including the plugin name, package/distribution, installed version, and Python entry point.
- **Refresh installed plugins** — Refresh the plugin list directly from the configuration page after installing or updating a plugin.
- **Installer status and output** — Installation results and pip output are shown in the web interface to make troubleshooting easier.
- **Safer GitHub installation** — The installer accepts direct HTTPS GitHub repository URLs while rejecting arbitrary pip arguments, local paths, SSH URLs, embedded credentials, query strings, and non-GitHub sources.
- **Retains V2.2 features** — Pi hostname and configurator authentication management, automatic creation of missing `teams.json` and `scoreboard.json` files from their example files, Wi-Fi/hotspot management, scoreboard service controls, configuration editing, RGB color controls, backups, and validation remain available.

## Requirements

- Raspberry Pi OS or another Linux distribution using NetworkManager.
- `nmcli`.
- MLB-LED-Scoreboard installed (default path `/home/pi/mlb-led-scoreboard`).
- Python virtual environment created by MLB-LED-Scoreboard.

## Install from Git

From the MLB-LED-Scoreboard directory:

```bash
cd ~/mlb-led-scoreboard
sudo venv/bin/pip install git+https://github.com/mcangeli/mlb-scoreboard-configurator.git
sudo venv/bin/mlb-scoreboard-configurator-setup
```

### First login

After setup, open:

```text
http://<raspberry-pi-ip>:8080
```

The default login is:

```text
Username: admin
Password: scoreboard
```

**Change the default password after your first login.** The web credentials are
stored in:

```text
/etc/mlb-scoreboard-configurator.env
```

Edit the file:

```bash
sudo nano /etc/mlb-scoreboard-configurator.env
```

Change these values as desired:

```text
CONFIGURATOR_USERNAME=admin
CONFIGURATOR_PASSWORD=scoreboard
```

Then restart the configurator so the new credentials take effect:

```bash
sudo systemctl restart mlb-scoreboard-configurator.service
```

You can verify the service is running with:

```bash
sudo systemctl status mlb-scoreboard-configurator.service
```


The first command installs the Python/Bullpen package into the scoreboard's
existing virtual environment.

The second command performs the privileged machine setup that pip should not do:
it installs/updates the systemd units, writes the environment file if necessary,
enables the Flask service, and enables the hotspot watchdog timer.

The setup command is **idempotent**. It is safe to run after every upgrade.

### Upgrade

```bash
cd ~/mlb-led-scoreboard
sudo venv/bin/pip install --upgrade git+https://github.com/mcangeli/mlb-scoreboard-configurator.git
sudo venv/bin/mlb-scoreboard-configurator-setup
```

### Local checkout install

```bash
cd ~/mlb-led-scoreboard
sudo venv/bin/pip install /path/to/mlb-scoreboard-configurator
sudo venv/bin/mlb-scoreboard-configurator-setup
```

### Nonstandard scoreboard location

Run setup from that scoreboard directory, or pass it explicitly:

```bash
sudo /path/to/venv/bin/mlb-scoreboard-configurator-setup \
  --root /srv/mlb-led-scoreboard
```

The setup command derives the installed venv executable paths rather than
hardcoding `/home/pi/mlb-led-scoreboard`.

## Hotspot

By default the fallback AP is:

```text
SSID: MLB-Scoreboard-Setup
Password: ScoreboardSetup
```

Change these in the web UI under **Wi-Fi**, or in:

```text
<scoreboard root>/.configurator/settings.json
```

The watchdog checks once per minute. If there is no active Wi-Fi client
connection it activates the hotspot. Once the Pi joins a Wi-Fi network, the
hotspot is stopped.

The default interface is `wlan0`. Override it with:

```bash
MLB_WIFI_INTERFACE=wlan1
```

in `/etc/mlb-scoreboard-configurator.env`.

## Security model

The two configurator services run as root because NetworkManager and systemd
control are privileged operations. The Flask portal is therefore protected by
HTTP Basic Authentication and should only be exposed on a trusted LAN or its
temporary setup hotspot.

For an Internet-exposed deployment, put it behind HTTPS/reverse proxy and use a
strong password.

## File safety

Before every save or restore, the old file is copied to:

```text
<scoreboard root>/.configurator/backups/
```

Writes are made to a temporary file and atomically replaced.

`config.json` is checked against the installed scoreboard's
`schemas/config.schema.json` when that schema is available. Other JSON files are
syntax checked and may be edited even when a future scoreboard release introduces
keys this UI does not know about.

## Bullpen integration

The package exposes:

```toml
[project.entry-points."bullpen.mlbled.plugin"]
configurator = "mlb_scoreboard_configurator.plugin:load"
```

The returned renderer deliberately never claims a rotation slot; the web portal
is a management utility rather than an LED screen.


## V3.0.0 plugin management

A new **Plugins** page appears under **System**. It can install a plugin from a direct GitHub repository URL into the scoreboard virtual environment with `venv/bin/pip install --upgrade git+<repository>`.

Only direct HTTPS GitHub repository URLs are accepted; arbitrary pip arguments and non-GitHub sources are rejected.

The page also lists Bullpen plugins registered through the `bullpen.mlbled.plugin` entry-point group, including entry-point name, package/distribution, version, and Python target.
