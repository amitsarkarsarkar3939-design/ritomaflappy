"use strict";

(() => {
  const output = document.getElementById("bix-output");
  const form = document.getElementById("bix-form");
  const input = document.getElementById("bix-input");
  const pathLabel = document.getElementById("sidebar-path");
  const boot = document.getElementById("bix-boot");
  const bootMessage = document.getElementById("boot-message");
  const submitButton = form.querySelector('button[type="submit"]');
  const commandForm = input.closest(".bix-command-form");
  const commandHistory = [];
  const completions = [
    "help",
    "game help",
    "game status",
    "game health",
    "game modes",
    "game profile classic",
    "game open",
    "pkg list",
    "pkg search",
    "pkg show",
    "pkg install",
    "pkg uninstall",
    "pwd",
    "ls",
    "clear"
  ];
  let historyIndex = 0;
  let busy = false;
  let cwd = "";
  let gameUrl = "http://127.0.0.1:8000/";

  document.body.classList.add("bix-game");
  document.title = "Bix Game Terminal";

  function addLine(text, kind = "system") {
    const line = document.createElement("div");
    line.className = `bix-line ${kind}`;
    line.textContent = text;
    output.append(line);
    output.scrollTop = output.scrollHeight;
  }

  function setPath(path) {
    cwd = path;
    pathLabel.textContent = path || "Game workspace";
    const home = commandForm.querySelector(".prompt-home");
    if (home) home.textContent = "game";
  }

  function configureGameWorkspace() {
    const brand = document.querySelector(".brand-terminal");
    if (brand) brand.textContent = " Game Terminal";
    const workspaceName = document.querySelector(".workspace-card strong");
    if (workspaceName) workspaceName.textContent = "Collect Ricoins";
    const noteTitle = document.querySelector(".sidebar-note strong");
    if (noteTitle) noteTitle.textContent = "Game console";
    const note = document.querySelector(".sidebar-note p");
    if (note) note.textContent = "Check your game status, modes, profile, and tools.";
    const workspace = document.querySelector(".bix-workspace");
    if (workspace) workspace.setAttribute("aria-label", "Collect Ricoins game terminal");
    const heading = document.querySelector(".terminal-heading h1");
    if (heading) heading.textContent = "Game terminal";
    const terminalBar = document.querySelector(".bix-window .terminal-bar strong");
    if (terminalBar) terminalBar.textContent = "ricoins://game";
    const safeBadge = document.querySelector(".safe-badge");
    if (safeBadge) {
      Array.from(safeBadge.childNodes)
        .filter((node) => node.nodeType === Node.TEXT_NODE)
        .forEach((node) => { node.textContent = " Local game service"; });
    }
    const footer = document.querySelectorAll(".terminal-footer span");
    if (footer[0]) footer[0].textContent = "Connected to the local game service.";
    if (footer[1]) footer[1].textContent = "Tools use an isolated game environment.";
    const sidebarFooter = document.querySelector(".sidebar-footer");
    if (sidebarFooter) sidebarFooter.textContent = "GAME CONSOLE · LOCAL";
    output.setAttribute("aria-label", "Game terminal output");
    input.placeholder = "Try: game status";
    const gameLink = document.querySelector(".game-link");
    if (gameLink) {
      gameLink.textContent = "Open game";
      gameLink.href = gameUrl;
    }

    const shortcuts = [
      ["?", "help", "Help"],
      ["◎", "game status", "Game status"],
      ["◈", "game modes", "Game modes"],
      ["⬡", "pkg list", "Game tools"]
    ];
    document.querySelectorAll("[data-command]").forEach((button, index) => {
      const shortcut = shortcuts[index];
      if (!shortcut) return;
      const key = button.querySelector("kbd");
      if (key) key.textContent = shortcut[0];
      const textNodes = Array.from(button.childNodes).filter(
        (node) => node.nodeType === Node.TEXT_NODE
      );
      if (textNodes.length) {
        textNodes[textNodes.length - 1].textContent = ` ${shortcut[2]}`;
      } else {
        button.append(document.createTextNode(` ${shortcut[2]}`));
      }
      button.dataset.command = shortcut[1];
    });
  }

  function showWelcome() {
    addLine("Bix Game Terminal · Collect Ricoins workspace", "welcome-title");
    addLine("Check the game service, browse modes, or inspect your profile.", "system");
    addLine("Type help for commands. Use ↑ and ↓ for command history.", "muted");
    addLine("", "spacer");
  }

  function setBusy(value) {
    busy = value;
    input.disabled = value;
    submitButton.disabled = value;
    form.setAttribute("aria-busy", String(value));
  }

  async function runCommand(command) {
    const trimmed = command.trim();
    if (!trimmed || busy) return;

    commandHistory.push(trimmed);
    historyIndex = commandHistory.length;
    addLine(`game:${cwd ? "workspace" : "~"} $ ${trimmed}`, "command");
    input.value = "";
    setBusy(true);

    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch("/api/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: trimmed }),
        signal: controller.signal
      });
      let result;
      try {
        result = await response.json();
      } catch {
        throw new Error(`The terminal returned an invalid response (${response.status}).`);
      }
      if (!response.ok) {
        throw new Error(result.error || `Request failed (${response.status}).`);
      }
      if (result.clear) output.replaceChildren();
      if (result.output) {
        result.output.split(/\r?\n/).forEach((line) => {
          addLine(line, result.ok ? "result" : "error");
        });
      } else if (!result.clear) {
        addLine("", "spacer");
      }
      if (result.cwd) setPath(result.cwd);
    } catch (error) {
      const message = error.name === "AbortError"
        ? "The game terminal did not respond within 15 seconds."
        : error.message;
      addLine(`Could not run command: ${message}`, "error");
    } finally {
      window.clearTimeout(timeout);
      setBusy(false);
      input.focus();
    }
  }

  function completeCommand() {
    const current = input.value.trim().toLowerCase();
    if (!current) return;
    const candidate = completions.find(
      (item) => item.startsWith(current) && item !== current
    );
    if (candidate) input.value = `${candidate} `;
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    runCommand(input.value);
  });

  input.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "l") {
      event.preventDefault();
      output.replaceChildren();
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      if (historyIndex > 0) input.value = commandHistory[--historyIndex];
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      if (historyIndex < commandHistory.length - 1) {
        input.value = commandHistory[++historyIndex];
      } else {
        historyIndex = commandHistory.length;
        input.value = "";
      }
    } else if (event.key === "Tab") {
      event.preventDefault();
      completeCommand();
    }
  });

  document.querySelectorAll("[data-command]").forEach((button) => {
    button.addEventListener("click", () => runCommand(button.dataset.command));
  });

  document.getElementById("clear-terminal").addEventListener("click", () => {
    output.replaceChildren();
    input.focus();
  });

  async function initialize() {
    configureGameWorkspace();
    const bootMessages = [
      "Loading the game console...",
      "Connecting to your local workspace...",
      "Ready."
    ];
    for (const message of bootMessages) {
      bootMessage.textContent = message;
      await new Promise((resolve) => window.setTimeout(resolve, 300));
    }
    boot.classList.add("boot-hidden");
    window.setTimeout(() => boot.remove(), 500);

    try {
      const response = await fetch("/api/status", { cache: "no-store" });
      if (!response.ok) throw new Error(`Terminal service unavailable (${response.status}).`);
      const result = await response.json();
      gameUrl = result.game_url || gameUrl;
      const gameLink = document.querySelector(".game-link");
      if (gameLink) gameLink.href = gameUrl;
      setPath(result.cwd);
      showWelcome();
      input.focus();
    } catch (error) {
      setPath("");
      addLine(error.message, "error");
      addLine("Keep the terminal launcher running, then reload this page.", "muted");
    }
  }

  initialize();
})();
