# MLB LED Scoreboard Configurator — V2.2.0

A Bullpen-compatible Flask web configurator for
[MLB-LED-Scoreboard](https://github.com/MLB-LED-Scoreboard/mlb-led-scoreboard),
targeting the v9 configuration model.

## V2 highlights

- Friendly structured form editor plus a raw JSON editor.
- Uses the scoreboard's local `schemas/config.schema.json` to validate `config.json`.
- Edits `config.json`, `colors/teams.json`, `colors/scoreboard.json`, and every
  `coordinates/*.json` file.
- Detects RGB triplets such as `[255, 0, 0]` and provides a visual color picker.
- Recursive coordinate/value editor for layout JSON.
- Automatic timestamped backups, backup browser, and restore support.
- Wi-Fi scan/status/connect/disconnect through NetworkManager (`nmcli`).
- Configurable fallback hotspot for first-run/headless setup.
- A separate hotspot watchdog systemd service can enable the setup AP when the Pi
  has no client Wi-Fi connection.
- Start/stop/restart/status actions for `mlb-led-scoreboard.service`.
- HTTP Basic Authentication on the configuration portal.
- Atomic config writes.
- Bullpen entry point is retained, but the web service is intentionally independent
  of scoreboard rendering so configuration remains available when the board is down.

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


## V2.1.1 fix

The setup command now detects the scoreboard virtualenv correctly when invoked
with `sudo venv/bin/mlb-scoreboard-configurator-setup`. V2.1 could incorrectly
use `/usr/bin` because `sudo` may cause Python interpreter discovery to resolve
outside the scoreboard venv.

You can still override detection explicitly with:

```bash
sudo venv/bin/mlb-scoreboard-configurator-setup \
  --root "$(pwd)" \
  --venv-bin "$(pwd)/venv/bin"
```


## V2.1.2 documentation update

The installation section now shows the configurator URL, default username and
password, the location of the credentials file, and the commands needed to
change credentials and restart the service.


## V2.1.3 editor file-switching fix

Fixed the configuration-file selector so choosing `config.json`,
`colors/teams.json`, `colors/scoreboard.json`, or a coordinates file reliably
reloads the structured editor and raw JSON editor.

The browser now waits for each selection request, displays a loading state,
ignores stale out-of-order responses, disables caching for configuration API
and static asset requests, and restores the previous selection if loading a
file fails.


## V2.1.4 color editor improvement

RGB color values in `colors/teams.json` and `colors/scoreboard.json` are shown
as visual GUI color controls. Click the large color swatch to open the browser's
native color picker. The R, G, and B numeric fields remain available for exact
values and stay synchronized with the picker. The hexadecimal and RGB values
are displayed alongside the swatch.

Colors are still written to the scoreboard JSON files in the original
`[R, G, B]` array format.


## V2.1.5 built-in color picker

Replaced the browser-dependent native color input with an in-page HSV color
picker. Every RGB color now has Hue, Saturation, and Brightness sliders plus
the existing R/G/B numeric fields and live color preview.

This works without relying on the operating system's color dialog and is
therefore consistent on Raspberry Pi browsers such as Firefox/Chromium.

The saved JSON format remains `[R, G, B]`.


## V2.1.6 visible version number

The configurator web interface now displays the installed package version in
the page header (for example, `v2.1.6`). This makes it easy to confirm that a
Git/pip upgrade has actually reached the Raspberry Pi and the running web UI.


## V2.1.7 startup fix

Fixed a V2.1.6 packaging regression where the version import was accidentally
inserted inside the multi-line `storage` import statement in `web.py`. That
syntax error prevented the Flask/Waitress configurator service from starting.

The version badge remains visible in the web interface. A regression test now
imports the web application and verifies that the rendered page contains the
installed version number.


## V2.1.8 visual editing improvements

### True in-page color picker

RGB values now use a two-dimensional saturation/brightness picker with a
separate hue slider. Clicking or dragging anywhere in the color square updates
the selected color immediately. The hue slider, live preview, hexadecimal
display, and R/G/B numeric fields all stay synchronized.

This implementation is fully rendered by the configurator itself and does not
depend on Firefox, Chromium, or the Raspberry Pi desktop environment providing
a native color chooser.

### Add/remove configuration items

Every object/configuration section now has an **Add item** button. You can enter
a key and choose an initial value type: text, number, boolean, section/object,
list/array, or RGB color.

Arrays also have an **Add list item** button, and both object properties and
array items can be removed directly from the form editor.

Schema-defined missing properties are suggested by the browser where available.
All additions/removals update the same JSON structure used by the raw editor and
are still validated before saving.


## V2.1.9 config rendering and MLB color-format fix

Fixed two issues found in V2.1.8:

1. String values inside arrays (for example teams, divisions, leagues, and
   rotation screen settings in `config.json`) no longer crash the structured
   editor. The full configuration now continues rendering after array values.
2. MLB-LED-Scoreboard color files use objects such as
   `{"r": 255, "g": 235, "b": 59}`. The configurator now recognizes this
   native format as a color and displays the 2D saturation/brightness picker,
   hue slider, preview, hex value, and R/G/B controls for it.

Both the native `{r,g,b}` representation and legacy `[r,g,b]` arrays are
supported. Edits preserve whichever representation was loaded.

The `$schema` and `format` fields are now visible in the structured editor,
and a render error boundary keeps the complete JSON available in Raw JSON mode
if an unexpected future configuration shape is encountered.


## V2.1.10 RGB object picker fix

Fixed a remaining array-only assumption in the visual color picker. The picker
now normalizes native MLB color objects such as `{"r":255,"g":235,"b":59}` to
an internal RGB array before any display/hex conversion is performed.

This removes the `value.map is not a function` error on `teams.json` and
`scoreboard.json` while preserving the original `{r,g,b}` structure when saved.


## V2.2.0 Pi / Configurator Settings page

A new **Pi / Configurator Settings** page is available from the sidebar.

It includes:

- Raspberry Pi hostname editing using `hostnamectl`.
- Configurator authentication username editing.
- New password + password confirmation fields.
- Authentication values are stored in `/etc/mlb-scoreboard-configurator.env`
  with mode `0600`.
- Existing unrelated configurator environment settings are preserved.
- A restart button is shown after changing authentication so the new login can
  be activated immediately.
- Hostname validation follows standard Linux hostname constraints.

Because the configurator service already runs as root for NetworkManager and
systemctl integration, no additional sudo configuration is required.


### Automatic creation of missing color files

V2.2.0 now checks for the live color configuration files before exposing them
in the web editor.

If `colors/teams.json` is missing and `colors/teams.example.json` exists, the
configurator creates `colors/teams.json` from that example file.

If `colors/scoreboard.json` is missing and `colors/scoreboard.example.json`
exists, the configurator creates `colors/scoreboard.json` from that example
file.

Existing live files are never overwritten. The example JSON is validated before
it is copied.
