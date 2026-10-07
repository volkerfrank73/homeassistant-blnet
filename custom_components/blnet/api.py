"""API client for BLNET."""

from __future__ import annotations


class BLNetApiClient:
    """Very small placeholder API client for BLNET."""

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port

    async def async_get_status(self) -> dict[str, object]:
        """Fetch the latest status from BLNET."""
        # Placeholder response to keep the integration functional during bootstrap.
        return {
            "available": True,
            "host": self._host,
            "port": self._port,
        }
