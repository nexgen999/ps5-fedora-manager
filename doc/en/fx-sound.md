# FX Sound (Easy Effects)

The **FX Sound** section (`audio-volume-high-symbolic`, right after *Services*).

It installs two things, one after the other:

1. **Easy Effects** — the system equalizer for PipeWire;
2. **JackHack96's community presets** — about a dozen ready-made settings, applied
   in one click.

Each row carries a **status badge** read from the system:

- **● Installed** — the `easyeffects` package is present (or presets exist);
- **○ Not installed** — nothing is installed;
- the presets row subtitle shows the **number of presets** found.

## 1. Easy Effects

The command the application runs (it already runs as root through `pkexec`, so no
internal `sudo`):

```bash
# dnf install -y easyeffects
```

Manual equivalent in a terminal:

```bash
$ sudo dnf install easyeffects

# Check the install
$ rpm -q easyeffects
$ easyeffects --version

# Launch the application
$ easyeffects
```

Easy Effects is a PipeWire plugin: there is **nothing to configure in PipeWire**, the
application creates its own virtual nodes on first launch.

## 2. Community presets (option 1: all)

The original command, exactly as launched by the application:

```bash
$ bash -c "$(curl -fsSL https://raw.githubusercontent.com/JackHack96/EasyEffects-Presets/master/install.sh)"
```

That script shows an interactive menu:

```
Please select an option for presets installation (Default=1)
1) Install all presets
2) Install Perfect EQ preset
3) Install all bass boosting presets
4) Install Advanced Auto Gain
5) Install Laptop speaker preset
6) Install loudness + autogain laptop preset
7) Install Dolby Atmos preset
8) Install Speaker Sync preset
```

The application **answers `1` automatically**, installing every preset with no
question asked. The command actually run is therefore:

```bash
$ printf '1\n' | bash <(curl -fsSL https://raw.githubusercontent.com/JackHack96/EasyEffects-Presets/master/install.sh)
```

Option 1 installs:

| Preset | Use |
|---|---|
| Perfect EQ | neutral equalization, a good starting point |
| Bass Enhancing + Perfect EQ | stronger bass |
| Bass Enhancing + Perfect EQ – Low Latency | same, lower latency (gaming) |
| Boosted | louder overall gain |
| Bass Boosted | pronounced bass |
| Advanced Auto Gain | constant volume across sources |
| Loudness + Autogain | loudness and automatic gain |
| Dolby Atmos | spatial rendering (headphones / HDMI) |
| Speaker Sync | speaker synchronization |
| Laptop | “small speaker” rendering |
| Impulse responses | `.irs` files used by some presets |

Presets are installed **for the desktop account**, never in `/root`: the script runs
with the real user's identity (`PKEXEC_UID` / `SUDO_USER`).

```
~/.local/share/easyeffects/
├── output/    # output presets (.json)
├── input/     # input presets (.json)
└── irs/       # impulse responses (.irs)
```

## 3. Using a preset

1. open **Easy Effects** from the applications menu;
2. open the **Presets** tab (or *Output* → *Presets*);
3. pick for instance **Dolby Atmos** or **Perfect EQ**;
4. check the output in **GNOME → Sound**: the PS5 usually outputs through **HDMI**.

Easy Effects must **stay running** (window or background) for the effects to apply;
this is real-time processing, not a setting written into the hardware.

## Useful checks

```bash
# Presets present
$ ls ~/.local/share/easyeffects/output | wc -l
$ ls ~/.local/share/easyeffects/irs | head

# Package installed and version
$ rpm -q easyeffects

# PipeWire devices / current output
$ pactl info | grep "Default Sink"
$ wpctl status

# Is Easy Effects running?
$ pgrep -a easyeffects
```

## Troubleshooting

| Symptom | Hint |
|---|---|
| “No preset installed” after installing | the script ran under another account: check the desktop user's `~/.local/share/easyeffects` |
| The script fails immediately | no network, or `curl` missing: `sudo dnf install curl` |
| Presets do not show up in the app | restart Easy Effects (presets are read at start-up) |
| No audible effect | Easy Effects is not running, or the wrong output is selected |
| No sound / crackles | choose a “Low Latency” preset, or enable fewer effects |
| `easyeffects` missing from the menu | sign out and back in (the `.desktop` file is cached) |

## Uninstalling

```bash
# Remove the presets (desktop account)
$ rm -rf ~/.local/share/easyeffects

# Remove the application
$ sudo dnf remove easyeffects
```

The section changes no system configuration file: removing the package and the
`~/.local/share/easyeffects` folder restores the original sound.
