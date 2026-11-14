"""Local, allowlisted Python package manager for the Bix game console."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.error
import urllib.request
import venv
import webbrowser
from contextlib import contextmanager
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parent
HOST = "127.0.0.1"
PORT = int(os.environ.get("BIX_TERMINAL_PORT", "8766"))
GAME_HOST = os.environ.get("GAME_HOST", "127.0.0.1")
GAME_PORT = int(os.environ.get("GAME_PORT", "8000"))
GAME_URL = f"http://{GAME_HOST}:{GAME_PORT}/"
HOME = Path(os.environ.get("BIX_HOME", Path.home() / ".bix-k0ns0le")).expanduser()
ENVIRONMENT = HOME / "python"
DATABASE = HOME / "packages.sqlite3"
MAX_COMMAND_LENGTH = 2048
INSTALL_TIMEOUT_SECONDS = 600
PACKAGE_LOCK = threading.Lock()

CATALOG: tuple[tuple[str, str, str, str], ...] = (
    ("pygame", "pygame", "pip", "Pygame game development library."),
    ("pygame-ce", "pygame-ce", "pip", "Community Edition of Pygame."),
    ("arcade", "arcade", "pip", "2D game development library."),
    ("pymunk", "pymunk", "pip", "2D physics simulation library."),
    ("pillow", "Pillow", "pip", "Image processing library (imported as PIL)."),
    ("pytmx", "pytmx", "pip", "TMX tile-map loader for Python games."),
    ("numpy", "numpy", "pip", "Array computing library."),
    ("sounddevice", "sounddevice", "pip", "Audio recording and playback library."),
    ("imageio", "imageio", "pip", "Image and animation input/output library."),
    ("pytest", "pytest", "pip", "Python testing framework."),
    ("json", "", "builtin", "Python standard-library JSON module."),
    ("time", "", "builtin", "Python standard-library time module."),
    ("logging", "", "builtin", "Python standard-library logging module."),
    ("sqlite3", "", "builtin", "Python standard-library SQLite module."),
    ("python", "", "runtime", "The Python runtime running this package manager."),
)
PACKAGE_ALIASES = {"pythpn": "python"}
PACKAGE_CONFLICTS = {"pygame": "pygame-ce", "pygame-ce": "pygame"}
ALLOWED_HOSTS = {f"127.0.0.1:{PORT}", f"localhost:{PORT}"}


@contextmanager
def _database() -> Iterator[sqlite3.Connection]:
    HOME.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE, timeout=15)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 15000")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_package_store() -> None:
    with _database() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS package_catalog (
                name TEXT PRIMARY KEY,
                distribution TEXT NOT NULL,
                kind TEXT NOT NULL,
                description TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS installed_packages (
                name TEXT PRIMARY KEY,
                version TEXT NOT NULL,
                installed_at INTEGER NOT NULL
            );
            """
        )
        connection.executemany(
            "INSERT OR IGNORE INTO package_catalog "
            "(name, distribution, kind, description) VALUES (?, ?, ?, ?)",
            CATALOG,
        )


def _python_executable() -> Path:
    if os.name == "nt":
        return ENVIRONMENT / "Scripts" / "python.exe"
    return ENVIRONMENT / "bin" / "python"


def _package_name(name: str) -> str:
    normalized = name.strip().lower()
    return PACKAGE_ALIASES.get(normalized, normalized)


def _catalog_entry(name: str) -> sqlite3.Row | None:
    with _database() as connection:
        return connection.execute(
            "SELECT name, distribution, kind, description "
            "FROM package_catalog WHERE name = ?",
            (_package_name(name),),
        ).fetchone()


def _installed_version(name: str) -> str | None:
    with _database() as connection:
        row = connection.execute(
            "SELECT version FROM installed_packages WHERE name = ?",
            (_package_name(name),),
        ).fetchone()
    if row is None:
        return None
    return str(row["version"])


def _package_list() -> str:
    with _database() as connection:
        packages = connection.execute(
            "SELECT name, distribution, kind, description "
            "FROM package_catalog ORDER BY name"
        ).fetchall()
    lines = []
    for package in packages:
        name = str(package["name"])
        kind = str(package["kind"])
        version = _installed_version(name)
        if kind == "builtin":
            state = "[built-in]"
        elif kind == "runtime":
            state = f"[Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}]"
        elif version:
            state = f"[installed {version}]"
        else:
            state = "[available]"
        lines.append(f"{state} {name} — {package['description']}")
    return "\n".join(lines)


def _ensure_environment() -> None:
    if not _python_executable().is_file():
        venv.EnvBuilder(with_pip=True).create(ENVIRONMENT)


def _run_pip(*arguments: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    environment["PIP_NO_INPUT"] = "1"
    return subprocess.run(
        [str(_python_executable()), "-m", "pip", *arguments],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=INSTALL_TIMEOUT_SECONDS,
        check=False,
        env=environment,
    )


def _pip_version(distribution: str) -> str:
    result = _run_pip("show", distribution)
    if result.returncode == 0:
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.partition(":")[2].strip()
    return "installed"


def _install(name: str) -> tuple[bool, str]:
    package = _catalog_entry(name)
    if package is None:
        return False, f'Unknown package "{name}". Use `pkg search <word>` or `pkg list`.'
    package_name = str(package["name"])
    kind = str(package["kind"])
    if kind == "builtin":
        return True, f"{package_name} is part of Python's standard library; nothing to install."
    if kind == "runtime":
        return True, f"Python {sys.version.split()[0]} is already running this console."

    conflict = PACKAGE_CONFLICTS.get(package_name)
    if conflict and _installed_version(conflict):
        return False, (
            f"{package_name} conflicts with installed {conflict}. "
            f"Run `pkg uninstall {conflict}` first."
        )

    with PACKAGE_LOCK:
        try:
            _ensure_environment()
            result = _run_pip(
                "install",
                "--upgrade",
                "--index-url",
                "https://pypi.org/simple",
                str(package["distribution"]),
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return False, f"Could not install {package_name}: {error}"
        output = (result.stdout + result.stderr).strip()
        if result.returncode:
            return False, (
                f"pip could not install {package_name} (exit code {result.returncode}).\n"
                f"{output[-12000:]}"
            )
        try:
            version = _pip_version(str(package["distribution"]))
        except (OSError, subprocess.TimeoutExpired):
            version = "installed"
        with _database() as connection:
            connection.execute(
                "INSERT INTO installed_packages (name, version, installed_at) "
                "VALUES (?, ?, ?) ON CONFLICT(name) DO UPDATE SET "
                "version = excluded.version, installed_at = excluded.installed_at",
                (package_name, version, int(time.time())),
            )
        message = f"Installed {package_name} {version} in the Bix Python environment."
        return True, f"{message}\n{output[-12000:]}" if output else message


def _uninstall(name: str) -> tuple[bool, str]:
    package = _catalog_entry(name)
    if package is None:
        return False, f'Unknown package "{name}". Use `pkg list`.'
    package_name = str(package["name"])
    if str(package["kind"]) != "pip":
        return False, f"{package_name} is built into Python and cannot be uninstalled."
    if not _installed_version(package_name):
        return False, f"{package_name} is not installed."

    with PACKAGE_LOCK:
        try:
            _ensure_environment()
            result = _run_pip("uninstall", "--yes", str(package["distribution"]))
        except (OSError, subprocess.TimeoutExpired) as error:
            return False, f"Could not uninstall {package_name}: {error}"
        output = (result.stdout + result.stderr).strip()
        if result.returncode:
            return False, (
                f"pip could not uninstall {package_name} (exit code {result.returncode}).\n"
                f"{output[-12000:]}"
            )
        with _database() as connection:
            connection.execute(
                "DELETE FROM installed_packages WHERE name = ?", (package_name,)
            )
        message = f"Uninstalled {package_name}."
        return True, f"{message}\n{output[-12000:]}" if output else message


def _game_request(path: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"http://{GAME_HOST}:{GAME_PORT}{path}",
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=3) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("The game service returned an unexpected response.")
    return payload


def _game_command(arguments: list[str]) -> dict[str, Any]:
    if not arguments or arguments[0].lower() in {"help", "--help"}:
        return {
            "ok": True,
            "output": (
                "game status                 Show game service, modes, and classic profile\n"
                "game health                 Check the local game service\n"
                "game modes                  List game modes and descriptions\n"
                "game profile [mode]         Show best score and Ricoins for a mode\n"
                "game open                   Open Collect Ricoins in your browser\n"
                f"Game address: {GAME_URL}"
            ),
        }

    action, *values = arguments
    action = action.lower()
    if action in {"launch", "play"} and not values:
        action = "open"
    if action == "open" and not values:
        try:
            _game_request("/api/health")
        except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as error:
            return {
                "ok": False,
                "output": f"Game service is unavailable at {GAME_URL}: {error}",
            }
        if not webbrowser.open(GAME_URL):
            return {"ok": False, "output": f"Could not open a browser. Visit {GAME_URL}"}
        return {"ok": True, "output": f"Opened Collect Ricoins at {GAME_URL}"}

    if action == "health" and not values:
        try:
            result = _game_request("/api/health")
        except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as error:
            return {"ok": False, "output": f"Game service is unavailable: {error}"}
        return {
            "ok": bool(result.get("ok")),
            "output": "Game service is online." if result.get("ok") else "Game service reported unhealthy.",
        }

    if action == "modes" and not values:
        try:
            result = _game_request("/api/modes")
        except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as error:
            return {"ok": False, "output": f"Could not load game modes: {error}"}
        modes = result.get("modes")
        if not isinstance(modes, list):
            return {"ok": False, "output": "The game service returned an invalid mode list."}
        lines = []
        for mode in modes:
            if not isinstance(mode, dict):
                continue
            mode_id = str(mode.get("mode_id", "unknown"))
            name = str(mode.get("display_name", mode_id))
            description = str(mode.get("description", ""))
            lines.append(f"{mode_id}: {name} — {description}".rstrip())
        return {"ok": True, "output": "\n".join(lines) or "No game modes are available."}

    if action == "profile" and len(values) <= 1:
        mode = values[0].lower() if values else "classic"
        if not mode.isascii() or not mode.replace("-", "").replace("_", "").isalnum():
            return {"ok": False, "output": "Mode names may contain only letters, numbers, hyphens, and underscores."}
        try:
            result = _game_request(
                f"/api/profile?mode={urllib.parse.quote(mode, safe='')}"
            )
        except urllib.error.HTTPError as error:
            if error.code == 400:
                return {"ok": False, "output": f'Unknown game mode "{mode}". Run "game modes".'}
            return {"ok": False, "output": f"Could not load the game profile: HTTP {error.code}."}
        except (OSError, urllib.error.URLError, json.JSONDecodeError, ValueError) as error:
            return {"ok": False, "output": f"Could not load the game profile: {error}"}
        if "best" not in result or "balance" not in result:
            return {"ok": False, "output": "The game service returned an incomplete profile."}
        return {
            "ok": True,
            "output": f"{mode} profile · best score {result['best']} · {result['balance']} Ricoins",
        }

    if action == "status" and not values:
        health = _game_command(["health"])
        if not health["ok"]:
            return health
        modes = _game_command(["modes"])
        profile = _game_command(["profile", "classic"])
        if not modes["ok"] or not profile["ok"]:
            failed = modes if not modes["ok"] else profile
            return failed
        return {
            "ok": True,
            "output": "\n".join(
                [
                    str(health["output"]),
                    f"Modes available: {len(str(modes['output']).splitlines())}",
                    str(profile["output"]),
                ]
            ),
        }

    return {
        "ok": False,
        "output": 'Usage: game <status|health|modes|profile [mode]|open|launch>. Type "game help".',
    }


def run_command(command: str) -> dict[str, Any]:
    if len(command) > MAX_COMMAND_LENGTH:
        return {"ok": False, "output": "Command is too long."}
    try:
        parts = shlex.split(command)
    except ValueError as error:
        return {"ok": False, "output": f"Could not parse command: {error}"}
    if not parts:
        return {"ok": True, "output": ""}

    root = parts[0].lower()
    arguments = parts[1:]
    if root in {"exit", "quit"} and not arguments:
        return {"ok": True, "output": "Goodbye.", "exit": True}
    if root in {"help", "?"} and not arguments:
        return {
            "ok": True,
            "output": (
                "Bix Game Terminal · local game console\n"
                "game status                       Check the game and your classic profile\n"
                "game modes                        List game modes\n"
                "game profile [mode]               Show score and Ricoins\n"
                "game open                         Open Collect Ricoins\n"
                "pkg list                           List game and Python packages\n"
                "pkg search <word>                 Search the package catalog\n"
                "pkg show <package>                Show package details\n"
                "pkg install <package>             Install in the isolated game environment\n"
                "pkg uninstall <package>           Remove an installed package\n"
                "pwd                               Show the game workspace\n"
                "ls                                List workspace files\n"
                "clear                             Clear the console\n"
                "Python packages are installed in an isolated environment. "
                "This game console does not run arbitrary operating-system commands."
            ),
        }
    if root == "clear" and not arguments:
        return {"ok": True, "output": "", "clear": True}
    if root == "pwd" and not arguments:
        return {"ok": True, "output": str(ROOT), "cwd": str(ROOT)}
    if root in {"ls", "dir"} and not arguments:
        names = sorted(path.name for path in ROOT.iterdir() if path.name != "__pycache__")
        return {"ok": True, "output": "\n".join(names), "cwd": str(ROOT)}

    if root == "game":
        return _game_command(arguments)

    if root in {"bic-v", "bix", "pkg"}:
        if not arguments:
            return {
                "ok": False,
                "output": "Usage: pkg <list|search|show|install|uninstall> [package].",
            }
        action, *values = arguments
        action = action.lower()
        if action in {"help", "--help"} and not values:
            return run_command("help")
        if action in {"list", "installed"} and not values:
            return {"ok": True, "output": _package_list()}
        if action == "search" and values:
            query = " ".join(values).lower()
            with _database() as connection:
                entries = connection.execute(
                    "SELECT name, description FROM package_catalog "
                    "WHERE lower(name) LIKE ? OR lower(description) LIKE ? ORDER BY name",
                    (f"%{query}%", f"%{query}%"),
                ).fetchall()
            output = "\n".join(
                f"{entry['name']} — {entry['description']}" for entry in entries
            )
            return {"ok": True, "output": output or "No packages matched that search."}
        if action == "show" and len(values) == 1:
            package = _catalog_entry(values[0])
            if package is None:
                return {"ok": False, "output": f'Unknown package "{values[0]}".'}
            version = _installed_version(str(package["name"]))
            status = version or (
                "built into Python" if package["kind"] != "pip" else "not installed"
            )
            distribution = (
                f"PyPI distribution: {package['distribution']}"
                if package["distribution"]
                else ""
            )
            return {
                "ok": True,
                "output": f"{package['name']} · {status}\n{package['description']}\n{distribution}".rstrip(),
            }
        if action == "install" and len(values) == 1:
            ok, output = _install(values[0])
            return {"ok": ok, "output": output}
        if action in {"uninstall", "remove"} and len(values) == 1:
            ok, output = _uninstall(values[0])
            return {"ok": ok, "output": output}
        return {
            "ok": False,
            "output": "Usage: pkg <list|search <word>|show <package>|install <package>|uninstall <package>>.",
        }

    return {
        "ok": False,
        "output": "This game console only runs game, workspace, and pkg commands. Type `help`.",
    }


class BixRequestHandler(SimpleHTTPRequestHandler):
    server_version = "BixGameTerminal/1.0"

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        print(f"[bix-game-terminal] {self.address_string()} {format % args}")

    def _local_request(self, require_origin: bool = False) -> bool:
        if self.headers.get("Host", "").lower() not in ALLOWED_HOSTS:
            self.send_error(403, "Use the local Bix console address.")
            return False
        origin = self.headers.get("Origin")
        if require_origin and origin not in {
            f"http://{host}" for host in ALLOWED_HOSTS
        }:
            self.send_error(403, "Requests must come from the Bix console.")
            return False
        return True

    def _json_response(self, status: int, data: dict[str, Any]) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if not self._local_request():
            return
        if self.path == "/api/status":
            self._json_response(
                200,
                {
                    "ok": True,
                    "cwd": str(ROOT),
                    "name": "Bix Game Terminal",
                    "game_url": GAME_URL,
                },
            )
            return
        if self.path == "/api/health":
            self._json_response(200, {"ok": True})
            return
        if self.path == "/":
            self.path = "/terminal.html"
        super().do_GET()

    def do_POST(self) -> None:
        if not self._local_request(require_origin=True):
            return
        if self.path != "/api/command":
            self._json_response(404, {"error": "Not found."})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json_response(400, {"error": "Invalid request length."})
            return
        if length < 1 or length > MAX_COMMAND_LENGTH + 1024:
            self._json_response(413, {"error": "Command request is too large."})
            return
        try:
            body = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json_response(400, {"error": "Request must contain valid JSON."})
            return
        if not isinstance(body, dict) or not isinstance(body.get("command"), str):
            self._json_response(400, {"error": "A command string is required."})
            return
        self._json_response(200, run_command(body["command"]))


def start_server() -> ThreadingHTTPServer:
    initialize_package_store()
    server = ThreadingHTTPServer((HOST, PORT), BixRequestHandler)
    server.daemon_threads = True
    return server


def local_service_is_ready() -> bool:
    try:
        request = urllib.request.Request(
            f"http://{HOST}:{PORT}/api/health",
            headers={"Host": f"{HOST}:{PORT}"},
        )
        with urllib.request.urlopen(request, timeout=1) as response:
            result = json.loads(response.read())
        return response.status == 200 and result.get("ok") is True
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Bix game terminal and package manager.")
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Run the game console in this terminal instead of opening the web UI.",
    )
    arguments = parser.parse_args()
    if arguments.cli:
        initialize_package_store()
        print("Bix Game Terminal · type help for commands, exit to quit.")
        while True:
            try:
                command = input("game> ")
            except EOFError:
                print()
                return
            except KeyboardInterrupt:
                print()
                continue
            result = run_command(command)
            if result.get("clear"):
                print("\033[2J\033[H", end="", flush=True)
            elif result.get("output"):
                print(result["output"])
            if result.get("exit"):
                return
        return

    address = f"http://{HOST}:{PORT}/terminal.html"
    if local_service_is_ready():
        print(f"Bix Game Terminal is already running at {address}")
        webbrowser.open(address)
        return
    server = start_server()
    print(f"Bix Game Terminal is running at {address}")
    print(f"Game packages use the isolated environment: {ENVIRONMENT}")
    print("Keep this window open while using the console. Press Ctrl+C to stop.")
    webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Bix Game Terminal.")
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
