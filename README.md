# redesigned-train
window-wsl-remote-debugging

## Chrome DevTools websocket from WSL

This repository includes a minimal bridge helper for keeping a Chrome DevTools remote debugging websocket alive from WSL, including localhost translation for:

`ws://127.0.0.1:PORT/devtools/browser/...`

When running under WSL, localhost DevTools endpoints are rewritten to the detected Windows host IP (or `CHROME_WINDOWS_HOST` if set), similar to `chrome-devtools-mcp` behavior.

### Usage

```bash
pip install websockets
python /tmp/workspace/donhat-dev/redesigned-train/wsl_chrome_devtools_ws.py ws://127.0.0.1:9222/devtools/browser/<id>
```

Resolve-only mode (no connection):

```bash
python /tmp/workspace/donhat-dev/redesigned-train/wsl_chrome_devtools_ws.py ws://127.0.0.1:9222/devtools/browser/<id> --resolve-only
```
