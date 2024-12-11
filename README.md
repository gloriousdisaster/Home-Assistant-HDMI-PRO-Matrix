# Gofanco Prophecy 4x4 HDMI Matrix (PRO-Matrix44-SC) Home Assistant Integration

This is a custom integration for Home Assistant that allows you to control your Gofanco Prophecy 4x4 HDMI Matrix **PRO-Matrix44-SC**.

![Company Icon](logos/icon.png)

## Disclaimer

I am not a programmer— just a Glorious Disaster! (Or maybe a glorious work in progress!) This is my first attempt at creating a Home Assistant (HA) integration. I reverse-engineered the Web API calls for the device, but I relied heavily on ChatGPT-4 o1 (Preview) and Claude 3.5 (Sonnet Preview) for assistance in generating and debugging the python code.

---

![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Custom%20Component-blue)
![HACS](https://img.shields.io/badge/HACS-Integration-green)
![GitHub Release](https://img.shields.io/github/v/release/gloriousdisaster/Home-Assistant-HDMI-PRO-Matrix)
![GitHub License](https://img.shields.io/github/license/gloriousdisaster/Home-Assistant-HDMI-PRO-Matrix)
![Maintenance](https://img.shields.io/maintenance/Limited/2024)

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

> [!Tip]  
> The gofanco PRO-Matrix44-SC defaults to a static IP of 192.168.1.70, as noted in the manual. Changing this requires a Windows PC, an RS232 connection, and the manufacturer’s Control Program. To simplify management (once and done), configure the device to use DHCP and set a reservation in your router or DHCP server to maintain a consistent IP.

- **Matrix Device**: PRO-Matrix44-SC with IP control enabled and accessible to Home Assistant.
- **DHCP Reservation**: Highly recommended, as the integration does not track IP address changes.

---

## Installation

**This is a placeholder**

Itegration is not in the store yet.

```text
**Not in store yet**
### Installation via HACS (Recommended) -

1. Install [HACS](https://hacs.xyz/) if you haven’t already.
2. Search for `Gofanco Prophecy HDMI Matrix` in HACS under Integrations and install it.
3. Restart Home Assistant (yes, this step is important).
4. Add the integration in Home Assistant:
   - Go to **Settings** > **Integrations** > **Add Integration**.
   - Search for `HDMI Matrix`.
   - Enter your device’s IP address.

Not familiar with HACS? Check out their [documentation](https://hacs.xyz/) for guidance.
```

## [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=gloriousdisaster&repository=Home-Assistant-HDMI-PRO-Matrix&category=Integration)

### Manual Installation

1. Navigate to your Home Assistant configuration directory (where `configuration.yaml` resides).
2. Create a `custom_components` folder if it doesn’t exist.
3. Inside `custom_components`, create a folder named `gofanco_prophecy`.
4. Download the files from this repository’s `custom_components/gofanco_prophecy/` directory.
5. Place the downloaded files into your `gofanco_prophecy` folder.
6. Restart Home Assistant.
7. Add the integration in the Home Assistant UI.
   - Go to **Settings** > **Integrations** > **Add Integration**.
   - Search for `HDMI Matrix`.
   - Enter your device’s IP address.

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

The following `curl` command retrieves general available parameters from the device:

```bash
curl --http0.9 -X POST "http://IP-ADDRESS/inform.cgi?undefined" \
     -H "Content-Type: application/json" \
     -d '{"param1":"1"}'
```

### Mute All Outputs (Set to Input 0)

The following `curl` command sets all outputs to input 0, effectively muting all outputs on the device:

```bash
curl --http0.9 -X POST "http://IP-ADDRESS/inform.cgi?undefined" \
     -H "Content-Type: application/json" \
     -d '{"outa":"0"}'
```

Replace IP-ADDRESS with your device’s actual IP.

### More POST Payload Information

A "param1" response will look something like this.

```text
{"out1":"1","out2":"2","out3":"4","out4":"0","namein1":"AVR","namein2":"Xbox","namein3":"PiKVM","namein4":"Aux","nameout1":"TV","nameout2":"Disp2","nameout3":"Dsp3","nameout4":"Dsp4","powstatus":"1"}%
```

#### Payloads

- Outputs [o] [1-4]
- Inputs [i] [0-4]
- Input 0 = Mute
- Maps [m] [1-8] (Maps are presets for multiple I/O settings)

| Payload           | Response           | Description                                |
| ----------------- | ------------------ | ------------------------------------------ |
| "param1":"1"      |                    | Gets I/O Assessments & Names, Power Status |
|                   | "out[o]":"[i]      | Output to Input                            |
|                   | "namein[i]":"[n]"  | Input Name                                 |
|                   | "nameout[o]":"[n]" | Output Name                                |
|                   | "powstatus":"[v]"  | Power Status (Values 1=on 0=off)           |
| out[o]: [i]       |                    | Assigns [o] Output to [i] input            |
| "outa":"[i]"      |                    | Assigns All Outputs to [i]                 |
| "namein[i]":"[n]" |                    | Assign Input Friendly Name                 |
| "nameout[o]":[n]" |                    | Assign Output Friendly Name                |
| mname[m]?[n]      |                    | Assigns Map Friendly Name                  |
| poweron           |                    | Power On Action                            |
| poweroff          |                    | Power Off Action                           |
| LOADNAME:         |                    | Get I/O Names                              |
| LOADMAP:          |                    | Get Map Names                              |
| save: [m]         |                    | Save Map (I/O Presets)                     |
| call: [m]         |                    | Calls Map (I/O Presets)                    |

## Known Issues

- Known Issues

  - This integration may have bugs (I’m still discovering them).
  - When adding the device, there is no current checks in place if you were to enter an incorrect IP address or the device was unreachable. The device in HA will be created, but the entities will not function.
  - _Note_: The HDMI Matrix is referred to as an HDMI Switch(er) in some parts of the code; while technically referred to as a matrix, it functions as a switching device and I used the terms interchangeably.
  - Feel free to [report issues](https://github.com/gloriousdisaster/Home-Assistant-HDMI-PRO-Matrix/issues).

---

## Contributing

Contributions are always welcome! If you come across any bugs or have feature suggestions, feel free to share them. While my Python skills are somewhat limited, I'm eager to collaborate and see what we can achieve together!

Submit Issues: Report bugs or suggest features in the GitHub issues section.
Fork and Contribute: If you want to make changes, fork the repository and submit a pull request.

---

## License

This project is licensed under the [MIT License](LICENSE).
No warranty of any kind, but you can do whatever you want with it.
