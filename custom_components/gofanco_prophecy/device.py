# device.py

"""
Device handler for the HDMI Switcher.

This module handles communication with the HDMI Switcher device,
including sending commands and parsing responses.
"""

import socket
import logging
import json

_LOGGER = logging.getLogger(__name__)


class HDMISwitcherDataHandler:
    """Class to handle data communication with the HDMI Switcher."""

    def __init__(self, host, port):
        """Initialize the data handler."""
        self.host = host
        self.port = port
        self.data = {}  # Stores the latest data from the device
        self.input_names = (
            {}
        )  # Maps input numbers to their names (including 'Mute')
        self.output_names = {}  # Maps output numbers to their names

    def update(self):
        """Fetch the latest data from the HDMI Switcher."""
        response = send_raw_http_request(self.host, self.port)
        if response.startswith("Error"):
            _LOGGER.error(
                "Error fetching data from HDMI Switcher: %s", response
            )
            return
        data = parse_response(response)
        if data:
            self.data = data
            self._extract_names(data)

    def set_output_input(self, output_num, input_num):
        """Set a specific output to a specific input."""
        body = f"out{output_num}={input_num}"
        response = send_raw_http_request(self.host, self.port, body=body)
        if response.startswith("Error"):
            _LOGGER.error(
                "Error setting output %s to input %s: %s",
                output_num,
                input_num,
                response,
            )
            return False
        self.update()  # Refresh data after setting
        return True

    def set_all_outputs_input(self, input_num):
        """Set all outputs to a specific input."""
        body = f"outa={input_num}"
        response = send_raw_http_request(self.host, self.port, body=body)
        if response.startswith("Error"):
            _LOGGER.error(
                "Error setting all outputs to input %s: %s",
                input_num,
                response,
            )
            return False
        self.update()  # Refresh data after setting
        return True

    def mute_all_outputs(self):
        """Mute all outputs."""
        body = "outa=0"
        response = send_raw_http_request(self.host, self.port, body=body)
        if response.startswith("Error"):
            _LOGGER.error("Error muting all outputs: %s", response)
            return False
        self.update()  # Refresh data after setting
        return True

    def power_on(self):
        """Power on the HDMI Switcher."""
        response = send_raw_http_request(self.host, self.port, body="poweron")
        if response.startswith("Error"):
            _LOGGER.error("Error powering on the HDMI Switcher: %s", response)
            return False
        self.update()
        return True

    def power_off(self):
        """Power off the HDMI Switcher."""
        response = send_raw_http_request(
            self.host, self.port, body="poweroff"
        )
        if response.startswith("Error"):
            _LOGGER.error(
                "Error powering off the HDMI Switcher: %s", response
            )
            return False
        self.update()
        return True

    def set_names(self, input_names, output_names):
        """Set the names of inputs and outputs on the device."""
        # Construct the POST body according to the required format
        # Example: namein1?Name1?namein2?Name2?...
        # nameout1?Name1?nameout2?Name2?...
        body_parts = []
        for i in range(1, 5):
            name_in = input_names.get(str(i), f"Input {i}")
            body_parts.append(f"namein{i}?{name_in}?")
        for i in range(1, 5):
            name_out = output_names.get(str(i), f"Output {i}")
            body_parts.append(f"nameout{i}?{name_out}?")
        body = "".join(body_parts)

        response = send_raw_http_request(self.host, self.port, body=body)
        if response.startswith("Error"):
            _LOGGER.error(
                "Error setting names on HDMI Switcher: %s", response
            )
            return False
        self.update()  # Refresh data after setting
        return True

    def _extract_names(self, data):
        """Extract input and output names from the device data."""
        # Extract input names, including 'Mute' as input '0'
        self.input_names = {
            "0": "Mute",  # Mute option
            **{
                str(i): data.get(f"namein{i}", f"Input {i}")[:7]
                for i in range(1, 5)
            },
        }

        # Extract output names
        self.output_names = {
            str(i): data.get(f"nameout{i}", f"Output {i}")[:7]
            for i in range(1, 5)
        }


def send_raw_http_request(host, port, body=None):
    """Send a raw HTTP request to the HDMI Switcher."""
    if body is None:
        body = '{"param1":"1"}'  # Default body if none is provided

    # HTTP request details
    endpoint = "/inform.cgi?undefined"
    method = "POST"
    headers = {
        "Host": host,
        "Content-Type": "application/json",
        "Origin": f"http://{host}",
        "Referer": f"http://{host}/",
        "Content-Length": str(len(body)),
    }

    # Construct the HTTP request
    request_line = f"{method} {endpoint} HTTP/1.1\r\n"
    header_lines = "".join(
        f"{key}: {value}\r\n" for key, value in headers.items()
    )
    content = f"{request_line}{header_lines}\r\n{body}"

    try:
        # Create a socket connection to the device
        with socket.create_connection((host, port), timeout=10) as sock:
            # Send the HTTP request
            sock.sendall(content.encode("utf-8"))
            # Receive the response
            response = receive_large_response(sock)
            return response
    except socket.timeout as e:
        return f"Connection timed out: {e}"
    except socket.error as e:
        return f"Socket error: {e}"
    except ValueError as e:
        return f"Value error: {e}"


def receive_large_response(sock, buffer_size=4096):
    """Receive a potentially large response from the device."""
    response = []
    while True:
        chunk = sock.recv(buffer_size)
        if not chunk:
            break
        response.append(chunk.decode("utf-8"))
    return "".join(response)


def parse_response(response):
    """Parse the JSON response from the device."""
    try:
        # Attempt to parse the JSON data
        data = json.loads(response)
        return data
    except json.JSONDecodeError as e:
        _LOGGER.error("JSON decode error: %s", e)
        return {}
