"""Constants for the BLNET integration."""

from __future__ import annotations

DOMAIN = "blnet"

CONF_NODE = "can_node"

DEFAULT_PORT = 80
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 15

CONF_SOURCE = "source"
SOURCE_WEB = "web"
SOURCE_WEB_TA = "web_ta"
SOURCE_TA = "ta"
SOURCES = [SOURCE_WEB, SOURCE_WEB_TA, SOURCE_TA]

CONF_TA_PORT = "ta_port"
DEFAULT_TA_PORT = 40000
CONF_TA_RESET = "ta_reset"
CONF_NAMES = "names"
# The UVR1611 has 13 switching outputs; the dataset carries 16 bits.
MAX_OUTPUT = 13
