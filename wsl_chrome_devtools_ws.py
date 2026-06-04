from __future__ import annotations

import argparse
import asyncio
import logging
import os
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from urllib.parse import SplitResult, urlsplit, urlunsplit


LOCALHOST_HOSTS = {"127.0.0.1", "localhost", "::1"}
LOGGER = logging.getLogger(__name__)


def is_wsl() -> bool:
    if os.environ.get("WSL_DISTRO_NAME"):
        return True

    release = platform.uname().release.lower()
    return "microsoft" in release or "wsl" in release


def _first_resolver_nameserver(path: Path = Path("/etc/resolv.conf")) -> Optional[str]:
    try:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split()
            if len(parts) >= 2 and parts[0] == "nameserver":
                candidate = parts[1].strip()
                if candidate and candidate not in LOCALHOST_HOSTS:
                    return candidate
    except OSError:
        return None

    return None


def windows_host() -> str:
    env_host = os.environ.get("CHROME_WINDOWS_HOST")
    if env_host:
        return env_host

    resolver_host = _first_resolver_nameserver()
    if resolver_host:
        return resolver_host

    return "127.0.0.1"


def resolve_devtools_ws_url(url: str, *, force_windows_host: Optional[str] = None) -> str:
    parsed: SplitResult = urlsplit(url)
    if parsed.scheme not in {"ws", "wss"}:
        raise ValueError("DevTools endpoint must use ws:// or wss://")

    if not parsed.hostname:
        raise ValueError("DevTools endpoint is missing hostname")

    host = parsed.hostname
    if host in LOCALHOST_HOSTS and is_wsl():
        replacement_host = force_windows_host or windows_host()
        port_part = f":{parsed.port}" if parsed.port is not None else ""
        netloc = f"{replacement_host}{port_part}"
        if parsed.username:
            auth = parsed.username
            if parsed.password:
                auth = f"{auth}:{parsed.password}"
            netloc = f"{auth}@{netloc}"

        parsed = parsed._replace(netloc=netloc)

    return urlunsplit(parsed)


@dataclass
class ConnectionConfig:
    """Connection tuning values in seconds for ping checks and reconnect backoff."""

    ping_interval: float = 20.0
    ping_timeout: float = 20.0
    reconnect_delay: float = 1.0
    max_reconnect_delay: float = 15.0


async def keep_devtools_connection(
    url: str, config: Optional[ConnectionConfig] = None
) -> None:
    """Maintain a resilient websocket session to Chrome DevTools."""
    try:
        import websockets
    except ImportError as exc:  # pragma: no cover - checked at runtime
        raise RuntimeError(
            "Missing dependency 'websockets'. Install it with: pip install websockets"
        ) from exc

    resolved_url = resolve_devtools_ws_url(url)
    cfg = config or ConnectionConfig()
    delay = cfg.reconnect_delay

    while True:
        try:
            async with websockets.connect(
                resolved_url,
                ping_interval=cfg.ping_interval,
                ping_timeout=cfg.ping_timeout,
            ) as ws:
                delay = cfg.reconnect_delay
                while True:
                    await ws.recv()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            LOGGER.warning(
                "DevTools websocket disconnected from %s; reconnecting in %.1fs",
                resolved_url,
                delay,
                exc_info=exc,
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, cfg.max_reconnect_delay)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Maintain Chrome DevTools websocket connection from WSL by resolving "
            "ws://127.0.0.1:PORT/devtools/browser to Windows host when needed."
        )
    )
    parser.add_argument("url", help="Chrome DevTools websocket URL")
    parser.add_argument(
        "--resolve-only",
        action="store_true",
        help="Only print resolved websocket URL and exit",
    )
    return parser


def main() -> int:
    args = _build_arg_parser().parse_args()
    try:
        if args.resolve_only:
            print(resolve_devtools_ws_url(args.url))
            return 0

        asyncio.run(keep_devtools_connection(args.url))
        return 0
    except KeyboardInterrupt:
        return 130
    except (RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
