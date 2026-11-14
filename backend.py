"""A small cross-platform terminal with an allowlisted system package manager."""

from __future__ import annotations

import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Package:
    name: str
    description: str
    winget_id: str
    brew_id: str
    apt_id: str


PACKAGES = (
    Package("git", "Distributed version control", "Git.Git", "git", "git"),
    Package("node", "Node.js JavaScript runtime", "OpenJS.NodeJS.LTS", "node", "nodejs"),
    Package("python", "Python programming language", "Python.Python.3.13", "python", "python3"),
    Package("ripgrep", "Fast text search tool", "BurntSushi.ripgrep.MSVC", "ripgrep", "ripgrep"),
)
PACKAGE_BY_NAME = {package.name: package for package in PACKAGES}
COMMAND_TIMEOUT_SECONDS = 1800


def _load_settings() -> tuple[str, str, str]:
    config_path = Path(__file__).with_name("abcd.lua")
    source = config_path.read_text(encoding="utf-8")
    values = {}
    for key in ("title", "prompt", "package_command"):
        match = re.search(
            rf'^\s*{key}\s*=\s*"([^"]+)"\s*,?\s*$',
            source,
            re.MULTILINE,
        )
        if match is None:
            raise RuntimeError(f'Missing string setting "{key}" in {config_path}.')
        values[key] = match.group(1)
    return values["title"], values["prompt"], values["package_command"]


TITLE, PROMPT, PACKAGE_COMMAND = _load_settings()


class Terminal:
    def __init__(self) -> None:
        self.cwd = Path.cwd().resolve()
        self.history: list[str] = []
        self.platform_name = platform.system()
        self.package_manager, self.manager_command = self._find_package_manager()

    @staticmethod
    def _find_package_manager() -> tuple[str | None, str | None]:
        if os.name == "nt":
            manager, command = "winget", "winget"
        elif sys.platform == "darwin":
            manager, command = "brew", "brew"
        else:
            manager, command = "apt", "apt-get"
        executable = shutil.which(command)
        if executable is None:
            return manager, None
        return manager, executable

    def _package_id(self, package: Package) -> str:
        if self.package_manager == "winget":
            return package.winget_id
        if self.package_manager == "brew":
            return package.brew_id
        return package.apt_id

    def _package_status(self, package: Package) -> str:
        if self.manager_command is None:
            return "manager unavailable"
        package_id = self._package_id(package)
        try:
            if self.package_manager == "winget":
                result = subprocess.run(
                    [
                        self.manager_command,
                        "list",
                        "--id",
                        package_id,
                        "--exact",
                        "--source",
                        "winget",
                        "--disable-interactivity",
                    ],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=30,
                    check=False,
                )
                output = result.stdout + result.stderr
                if re.search(re.escape(package_id), output, re.IGNORECASE):
                    return "installed"
                if "no installed package found" in output.casefold():
                    return "not installed"
                return "status unknown" if result.returncode else "not installed"
            if self.package_manager == "brew":
                command = [self.manager_command, "list", "--versions", package_id]
            else:
                command = [
                    "dpkg-query",
                    "-W",
                    "-f=${Status}",
                    package_id,
                ]
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return "status unknown"
        if self.package_manager == "brew":
            return "installed" if result.returncode == 0 else "not installed"
        return (
            "installed"
            if result.returncode == 0 and result.stdout.strip() == "install ok installed"
            else "not installed"
        )

    def _package_action(self, action: str, package: Package) -> int:
        if self.manager_command is None:
            print(
                f"The {self.package_manager} package manager is not available on this system."
            )
            return 1

        package_id = self._package_id(package)
        if self.package_manager == "winget":
            command = [self.manager_command, action, "--id", package_id, "--exact"]
            command.extend(
                [
                    "--source",
                    "winget",
                    "--accept-package-agreements",
                    "--accept-source-agreements",
                    "--disable-interactivity",
                ]
            )
        elif self.package_manager == "brew":
            command = [self.manager_command, action, package_id]
        else:
            apt_action = "install" if action in {"install", "upgrade"} else "remove"
            apt_arguments = [self.manager_command, apt_action, "-y"]
            if action == "upgrade":
                apt_arguments.append("--only-upgrade")
            command = apt_arguments + ["--", package_id]
            if os.name != "nt" and hasattr(os, "geteuid") and os.geteuid() != 0:
                sudo = shutil.which("sudo")
                if sudo is None:
                    print("Package installation needs administrator privileges (sudo not found).")
                    return 1
                command.insert(0, sudo)

        verb = "upgrade" if action == "upgrade" else action
        print(f"Running {self.package_manager} {verb} for {package.name}...")
        try:
            result = subprocess.run(
                command,
                cwd=str(self.cwd),
                timeout=COMMAND_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"The package operation timed out after {COMMAND_TIMEOUT_SECONDS} seconds.")
            return 1
        except OSError as error:
            print(f"Could not start the package manager: {error}")
            return 1
        if result.returncode:
            print(f"Package operation failed with exit code {result.returncode}.")
        else:
            print(f"{package.name}: {verb} complete.")
        return result.returncode

    def _packages(self, arguments: list[str]) -> int:
        if not arguments or arguments[0] in {"help", "--help"}:
            print(
                f"Usage: {PACKAGE_COMMAND} <list|search|info|install|remove|upgrade> [name]\n"
                "Only packages in the built-in catalog can be installed or removed."
            )
            return 0

        action, *values = arguments
        action = action.lower()
        if action == "list" and not values:
            manager = self.package_manager or "unsupported"
            print(f"System package manager: {manager}")
            for package in PACKAGES:
                print(f"{package.name:10} {self._package_status(package):18} {package.description}")
            return 0
        if action == "search" and values:
            query = " ".join(values).casefold()
            matches = [
                package
                for package in PACKAGES
                if query in package.name.casefold() or query in package.description.casefold()
            ]
            for package in matches:
                print(f"{package.name:10} {package.description}")
            if not matches:
                print("No catalog packages matched.")
            return 0
        if action == "info" and len(values) == 1:
            package = PACKAGE_BY_NAME.get(values[0].casefold())
            if package is None:
                print(f'Unknown package "{values[0]}". Use "pkg search" to see the catalog.')
                return 1
            print(f"{package.name} — {package.description}")
            print(f"System package ID: {self._package_id(package)} ({self.package_manager})")
            print(f"Status: {self._package_status(package)}")
            return 0
        if action in {"install", "remove", "upgrade"} and len(values) == 1:
            package = PACKAGE_BY_NAME.get(values[0].casefold())
            if package is None:
                print(f'Unknown package "{values[0]}". Use "pkg search" to see the catalog.')
                return 1
            return self._package_action(action, package)
        if action == "upgrade" and values == ["all"]:
            installed = [
                package
                for package in PACKAGES
                if self._package_status(package) == "installed"
            ]
            if not installed:
                print("No installed catalog packages were found.")
                return 0
            return max(self._package_action("upgrade", package) for package in installed)

        print(
            "Usage: pkg <list|search <word>|info <name>|install <name>|"
            "remove <name>|upgrade <name|all>>"
        )
        return 2

    def _run_shell(self, command: str) -> int:
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(self.cwd),
                check=False,
            )
        except OSError as error:
            print(f"Could not start the system shell: {error}")
            return 1
        return result.returncode

    def execute(self, command: str) -> int:
        command = command.strip()
        if not command:
            return 0
        self.history.append(command)
        try:
            parts = shlex.split(command, posix=os.name != "nt")
            if os.name == "nt":
                parts = [
                    part[1:-1]
                    if len(part) >= 2 and part[0] == part[-1] and part[0] in {"'", '"'}
                    else part
                    for part in parts
                ]
        except ValueError as error:
            print(f"Could not parse command: {error}")
            return 2
        if not parts:
            return 0

        name = parts[0].casefold()
        arguments = parts[1:]
        if name in {"exit", "quit"} and not arguments:
            raise EOFError
        if name in {"help", "?"} and not arguments:
            self.print_help()
            return 0
        if name == PACKAGE_COMMAND.casefold():
            return self._packages(arguments)
        if name == "pwd" and not arguments:
            print(self.cwd)
            return 0
        if name in {"cd", "chdir"} and len(arguments) <= 1:
            target = Path(arguments[0]).expanduser() if arguments else Path.home()
            if not target.is_absolute():
                target = self.cwd / target
            try:
                resolved = target.resolve(strict=True)
            except OSError as error:
                print(f"Cannot change directory: {error}")
                return 1
            if not resolved.is_dir():
                print(f"Not a directory: {resolved}")
                return 1
            self.cwd = resolved
            return 0
        if name in {"ls", "dir"} and len(arguments) <= 1:
            target = Path(arguments[0]).expanduser() if arguments else self.cwd
            if not target.is_absolute():
                target = self.cwd / target
            try:
                for entry in sorted(target.iterdir(), key=lambda item: item.name.casefold()):
                    print(entry.name + (os.sep if entry.is_dir() else ""))
            except OSError as error:
                print(f"Cannot list directory: {error}")
                return 1
            return 0
        if name == "clear" and not arguments:
            print("\033[2J\033[H", end="", flush=True)
            return 0
        if name == "history" and not arguments:
            for index, item in enumerate(self.history, start=1):
                print(f"{index:4}  {item}")
            return 0
        return self._run_shell(command)

    @staticmethod
    def print_help() -> None:
        print(
            f"{TITLE}\n"
            "Type system commands to run them in your current folder.\n"
            "Built-ins: help, pwd, cd [folder], ls [folder], clear, history, exit\n"
            f"Packages: {PACKAGE_COMMAND} list | search <word> | info <name> | install <name>\n"
            f"          {PACKAGE_COMMAND} remove <name> | upgrade <name|all>\n"
            f"Package manager: {platform.system()} native manager, limited to {len(PACKAGES)} catalog entries."
        )

    def run(self) -> int:
        print(f"{TITLE} — {self.platform_name}")
        print('Type "help" for commands. System package changes require an explicit pkg command.')
        while True:
            try:
                command = input(f"{PROMPT}:{self.cwd}> ")
                self.execute(command)
            except EOFError:
                print("\nGoodbye.")
                return 0
            except KeyboardInterrupt:
                print()


def main() -> int:
    terminal = Terminal()
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
        try:
            return terminal.execute(command)
        except EOFError:
            return 0
    return terminal.run()


if __name__ == "__main__":
    raise SystemExit(main())
