# Gofanco Prophecy 4x4 HDMI Matrix (PRO-Matrix44-SC) Home Assistant Integration

This is a custom integration for Home Assistant that allows you to control your Gofanco Prophecy 4x4 HDMI Matrix **PRO-Matrix44-SC**.

![Company Icon](logos/icon.png)

## Disclaimer

I am not a programmer—just a Glorious Disaster!  
This is my first attempt at creating a Home Assistant (HA) integration. I relied heavily on ChatGPT-4 o1 (Preview) and Claude 3.5 (Sonnet Preview) for assistance in generating and debugging the code.

---

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Component-blue)
![HACS](https://img.shields.io/badge/HACS-Integration-green)
![GitHub Release](https://img.shields.io/github/v/release/gloriousdisaster/Home-Assistant-HDMI-PRO-Matrix)
![GitHub License](https://img.shields.io/github/license/gloriousdisaster/Home-Assistant-HDMI-PRO-Matrix)
![Maintenance](https://img.shields.io/maintenance/Minimally/2024)

---

## Features

This integration allows you to control your **PRO-Matrix44-SC HDMI Matrix** directly from Home Assistant.

### Supported Platforms

| Platform | Description                                        |
| -------- | -------------------------------------------------- |
| `switch` | Power the matrix on and off.                       |
| `select` | Toggle and view source of HDMI inputs and outputs. |
| `button` | Mute all outputs with a single command.            |

### Key Features

- **Input/Output Switching**: Route any of the 4 HDMI inputs to any of the 4 HDMI outputs.
  - Mute individual outputs or all outputs at once.
- **Power Control**: Turn the HDMI matrix on and off from Home Assistant.

---

## Requirements

- **Matrix Device**: PRO-Matrix44-SC with IP control enabled and accessible to Home Assistant.
- **DHCP Reservation**: Highly recommended, as the integration does not track IP address changes.

---

## Installation

### Installation via HACS (Recommended) - Not in store yet.

**This is a placeholder**

1. Install [HACS](https://hacs.xyz/) if you haven’t already.
2. Search for `Gofanco Prophecy HDMI Matrix` in HACS under Integrations and install it.
3. Restart Home Assistant (yes, this step is important).
4. Add the integration in Home Assistant:
   - Go to **Settings** > **Integrations** > **Add Integration**.
   - Search for `HDMI Switcher`.
   - Enter your device’s IP address.

Not familiar with HACS? Check out their [documentation](https://hacs.xyz/) for guidance.

### Manual Installation

1. Navigate to your Home Assistant configuration directory (where `configuration.yaml` resides).
2. Create a `custom_components` folder if it doesn’t exist.
3. Inside `custom_components`, create a folder named `hdmi_switcher`.
4. Download the files from this repository’s `custom_components/hdmi_switcher/` directory.
5. Place the downloaded files into your `hdmi_switcher` folder.
6. Restart Home Assistant.
7. Add the integration in the Home Assistant UI as described above.

---

## Supported Devices

This integration is designed for and tested with the [Prophecy 4x4 HDMI Matrix (PRO-Matrix44-SC)](https://www.gofanco.com/4k-hdr-4x4-matrix-with-downscaling-support-pro-matrix44-sc.html).

---

## Lovelace Dashboard Example

Here’s an example configuration for your Lovelace dashboard:

```yaml
type: entities
entities:
  - entity: switch.power
    name: Power
    icon: mdi:power
  - entity: select.output_1
    icon: mdi:remote
  - entity: select.output_2
    icon: mdi:remote
  - entity: select.output_3
    icon: mdi:remote
  - entity: select.output_4
    icon: mdi:remote
  - entity: select.output_all
  - entity: button.mute_all
    name: Mute All Outputs
    icon: mdi:volume-off
state_color: true
```

---

## How It Works

The PRO-Matrix44-SC uses an embedded web server with HTTP 0.9. I reverse-engineered its behavior by capturing network requests from its web GUI. Actions are triggered through simple HTTP POST requests.

## Example Usage with `curl`

### Retrieve General Parameters

The following `curl` command retrieves all available parameters from the device:

```bash
curl --http0.9 -X POST "http://IP-ADDRESS/inform.cgi?undefined" \
     -H "Content-Type: application/json" \
     -d '{"param1":"1"}'
```

### Mute All Outputs (Set to Input 0)

The following `curl` command sets all outputs to input 0, effectively muting the device:

```bash
curl --http0.9 -X POST "http://IP-ADDRESS/inform.cgi?undefined" \
     -H "Content-Type: application/json" \
     -d '{"outa":"0"}'
```

Replace IP-ADDRESS with your device’s actual IP.

### More POST Information

A "param1" response will look something like this.

```text
{"out1":"1","out2":"2","out3":"4","out4":"0","namein1":"AVR","namein2":"Xbox","namein3":"PiKVM","namein4":"Aux","nameout1":"TV","nameout2":"Disp2","nameout3":"Dsp3","nameout4":"Dsp4","powstatus":"1"}%
```

#### Payloads

- Outputs [o] [1-5]
- Inputs [i] [0-4]
- Output 0 = Mute
- Maps [m [1-8]] (Consider maps to be presets for multiple I/O settings)

| Payload           | Response           | Description                                |
| ----------------- | ------------------ | ------------------------------------------ |
| "param1":"1"      |                    | Gets I/O Assessments & Names, Power Status |
|                   | "out[o]":"[i]      | Output to Input                            |
|                   | "namein[i]":"[n]"  | Input Name                                 |
|                   | "nameout[o]":"[n]" | Output Name                                |
|                   | "powstatus":"[v]"  | Power Status (Values 1=on 0=off)           |
| out[o]: [i]       |                    | Assigns [o] Output to [i] input            |
| "outa":"[i]"      |                    | Assigns All Output to [i]                  |
| "namein[i]":"[n]" |                    | Assign Input Friendly Name                 |
| "nameout[o]":[n]" |                    | Assign Output                              |
| mname[m]?[n]      |                    | Assigns Map Friendly Name                  |
| poweroon          |                    | Power On Action                            |
| poweroff          |                    | Power Off Action                           |
| LOADNAME:         |                    | Get I/O Names                              |
| LOADMAP:          |                    | Get Map Names                              |
| save: [m]         |                    | Save Map (I/O Presets)                     |
| call: [m]         |                    | Calls Map (I/O Presets)                    |

## Known Issues

- Known Issues

  - This integration may have bugs (I’m still discovering them).
  - When adding the device, there is no current checks in place if you were to enter an incorrect IP address. The device will be created, but the entities will not function.
  - Feel free to [report issues](https://github.com/loriousdisaster/Home-Assistant-HDMI-PRO-Matrix-Alpha/issues).

---

## Contributing

I welcome contributions! If you encounter bugs or have feature suggestions, let me know.

Submit Issues: Report bugs or suggest features in the GitHub issues section.
Fork and Contribute: If you want to make changes, fork the repository and submit a pull request.

---

## License

This project is licensed under the [MIT License](LICENSE).
