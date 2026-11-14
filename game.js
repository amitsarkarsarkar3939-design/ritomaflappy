(() => {
  "use strict";

  const canvas = document.getElementById("game");
  const ctx = canvas.getContext("2d");
  const scoreElement = document.getElementById("score");
  const coinsElement = document.getElementById("coins");
  const bestElement = document.getElementById("best");
  const hintElement = document.getElementById("hint");
  const playerInput = document.getElementById("player-photo");
  const coinInput = document.getElementById("coin-photo");
  const modeSelect = document.getElementById("game-mode");
  const skinSelect = document.getElementById("game-skin");
  const modeDescription = document.getElementById("mode-description");
  const walletElement = document.getElementById("shop-wallet");
  const shopItemsElement = document.getElementById("shop-items");
  const installButton = document.getElementById("install-app");
  const accountForm = document.getElementById("account-form");
  const accountStatus = document.getElementById("account-status");
  const accountUsernameInput = document.getElementById("account-username");
  const accountPasswordInput = document.getElementById("account-password");
  const signInButton = document.getElementById("sign-in");
  const signUpButton = document.getElementById("sign-up");
  const signOutButton = document.getElementById("sign-out");
  const terminalOutput = document.getElementById("terminal-output");
  const terminalForm = document.getElementById("terminal-form");
  const terminalInput = document.getElementById("terminal-input");
  const soundEnabledInput = document.getElementById("sound-enabled");
  const soundVolumeInput = document.getElementById("sound-volume");
  const soundVolumeValue = document.getElementById("sound-volume-value");
  const resetSettingsButton = document.getElementById("reset-settings");

  const width = canvas.width;
  const height = canvas.height;
  const isAndroidApp = new URLSearchParams(window.location.search).get("android") === "1";
  const apiBase = "http://127.0.0.1:8765";
  const bird = { x: 118, y: 300, velocity: 0, radius: 19, rotation: 0, mouthAngle: 0, mouthTimer: 0, shieldTimer: 0 };
  const pipes = [];
  const tokens = [];
  const trail = [];
  const pipeWidth = 72;
  const shopItems = [
    { id: "wingsRainbow", type: "wings", name: "Rainbow wings", description: "Bright, shifting colors for every flight.", price: 20, color: ["#ff5364", "#ffcb45", "#53d58a", "#55baff", "#b278ff"] },
    { id: "wingsGolden", type: "wings", name: "Golden wings", description: "A shining golden look for Ritoma.", price: 25, color: ["#fff1a3", "#ffc02e", "#d98213"] },
    { id: "wingsDiamond", type: "wings", name: "Diamond wings", description: "Cool sparkling blues and icy cyan.", price: 30, color: ["#efffff", "#78eaff", "#5595ff"] },
    { id: "wingsRuby", type: "wings", name: "Ruby wings", description: "Deep red wings with a bright shine.", price: 35, color: ["#ff9b9b", "#ed234d", "#8e123b"] },
    { id: "wingsGod", type: "wings", name: "God wings", description: "A legendary glow of purple and gold.", price: 50, color: ["#fff5b0", "#ffad35", "#a45aff"] },
    { id: "trailRainbow", type: "trail", name: "Rainbow trail", description: "Leave a colorful rainbow sparkle trail.", price: 15, colors: ["#ff5364", "#ffcb45", "#53d58a", "#55baff", "#b278ff"] },
    { id: "trailGolden", type: "trail", name: "Golden trail", description: "Shimmer with golden sparks.", price: 15, colors: ["#fff1a3", "#ffc02e", "#d98213"] },
    { id: "trailRed", type: "trail", name: "Red trail", description: "Fly with bright red sparks.", price: 10, colors: ["#ff9b9b", "#ed234d", "#a31532"] },
    { id: "trailBlue", type: "trail", name: "Blue trail", description: "Leave a cool trail of blue sparks.", price: 10, colors: ["#b8edff", "#45b7f5", "#3659db"] },
    { id: "trailBrown", type: "trail", name: "Brown trail", description: "A warm trail of earthy sparks.", price: 10, colors: ["#d9aa76", "#986036", "#5d3828"] },
    { id: "trailWhite", type: "trail", name: "White trail", description: "Soft white clouds follow your flight.", price: 10, colors: ["#ffffff", "#e7f2ff", "#c5d5e8"] },
    { id: "trailYellow", type: "trail", name: "Yellow trail", description: "Bright sunshine-colored sparks.", price: 10, colors: ["#fff6a3", "#ffd52f", "#ff9f1c"] },
    { id: "trailPink", type: "trail", name: "Pink trail", description: "A playful trail of pink sparkles.", price: 10, colors: ["#ffd1ed", "#ff76bd", "#cf4dff"] },
    { id: "trailBlood", type: "trail", name: "Blood trail", description: "A dramatic dark crimson trail.", price: 15, colors: ["#bb1737", "#740d25", "#3b0818"] },
    { id: "trailGhost", type: "trail", name: "Ghost trail", description: "Pale, fading ghostly wisps.", price: 15, colors: ["#ffffff", "#c8eaff", "#9d9cff"] },
    { id: "shields", name: "Bubble shield", description: "A one-use shield that saves you from a pipe.", price: 12, ownedLabel: "Buy another" }
  ];
  const modes = {
    classic: {
      label: "Classic",
      description: "The balanced original challenge.",
      gravity: 1450,
      flapStrength: -440,
      pipeGap: 178,
      pipeSpeed: 190,
      spawnInterval: 1.65
    },
    chill: {
      label: "Chill",
      description: "Slower pipes and wider gaps for a more relaxed flight.",
      gravity: 1150,
      flapStrength: -405,
      pipeGap: 220,
      pipeSpeed: 150,
      spawnInterval: 1.9
    },
    speedy: {
      label: "Speedy",
      description: "Fast pipes and tighter gaps for a bigger challenge.",
      gravity: 1550,
      flapStrength: -455,
      pipeGap: 150,
      pipeSpeed: 250,
      spawnInterval: 1.5
    },
    horror: {
      label: "Horror",
      description: "Eerie skies, shadowy pipes, and a narrow escape.",
      gravity: 1500,
      flapStrength: -445,
      pipeGap: 160,
      pipeSpeed: 225,
      spawnInterval: 1.55
    },
    fun: {
      label: "Fun",
      description: "Floatier jumps, bouncy colors, and double Ricoins.",
      gravity: 1050,
      flapStrength: -390,
      pipeGap: 205,
      pipeSpeed: 175,
      spawnInterval: 1.8
    },
    extreme: {
      label: "Extreme",
      description: "Very fast pipes and the tightest gaps.",
      gravity: 1650,
      flapStrength: -470,
      pipeGap: 132,
      pipeSpeed: 285,
      spawnInterval: 1.4
    }
  };
  const skins = {
    sunny: {
      skyTop: "#83d9f3",
      skyBottom: "#d4f5f5",
      clouds: "#ffffff9c",
      hill: "#a6e3c2",
      ground: "#84d2a6",
      groundTop: "#65bd83",
      pipeLight: "#81df78",
      pipeDark: "#32a95f",
      pipeEdge: "#25854f",
      bird: "#ffd44e",
      birdEdge: "#e6a42e",
      tail: "#e99b38",
      beak: "#f08d37",
      coin: "#ffc83d",
      coinEdge: "#e69c1e"
    },
    sunset: {
      skyTop: "#ff9b83",
      skyBottom: "#ffe2a8",
      clouds: "#fff8d99c",
      hill: "#d9a1a0",
      ground: "#b77d87",
      groundTop: "#945e76",
      pipeLight: "#f2ae68",
      pipeDark: "#d46d59",
      pipeEdge: "#a84d54",
      bird: "#ffdd72",
      birdEdge: "#ea9a54",
      tail: "#db7658",
      beak: "#b84d50",
      coin: "#ffe16b",
      coinEdge: "#e69b39"
    },
    midnight: {
      skyTop: "#182b57",
      skyBottom: "#485b91",
      clouds: "#dbe6ff72",
      hill: "#536e91",
      ground: "#344e76",
      groundTop: "#243c67",
      pipeLight: "#74d7c3",
      pipeDark: "#399d9b",
      pipeEdge: "#277779",
      bird: "#b9e5ff",
      birdEdge: "#78b4e1",
      tail: "#779ce0",
      beak: "#ffbd69",
      coin: "#ffe178",
      coinEdge: "#e2a840"
    }
  };

  const packages = {
    "bird-tuner": { version: "1.2.0", latest: "1.3.0", description: "Bird physics tuning commands." },
    "sky-painter": { version: "1.1.0", latest: "1.2.0", description: "World skin and background commands." },
    "flight-lab": { version: "1.0.0", latest: "1.1.0", description: "Saveable flight-mod tools." }
  };
  let state = "ready";
  let score = 0;
  let coinCount = 0;
  let bestScores = readBestScores();
  let mode = readStoredChoice("flappy-ricoins-mode", modes, modeSelect.value);
  let skin = readStoredChoice("flappy-ricoins-skin", skins, skinSelect.value);
  let best = readBest(mode);
  let lastTime = 0;
  let spawnTimer = 0;
  let elapsed = 0;
  let playerImage = new Image();
  let coinImage = new Image();
  let shopState = readShopState();
  let customSettings = normalizeCustomSettings(readSavedObject("flappy-ricoins-physics"));
  let mods = normalizeMods(readSavedObject("flappy-ricoins-mods"));
  let installedPackages = readInstalledPackages();
  let packageVersions = readPackageVersions();
  let packageCatalogUpdated = readPackageCatalogVersion();
  let soundPreferences = readSoundPreferences();
  let audioContext = null;
  let authToken = isAndroidApp ? "" : readStoredToken();
  let accountName = "";
  let cloudSaveTimer = 0;
  playerImage.src = new URL("assets/player.jpg", document.baseURI).href;
  coinImage.src = new URL("assets/coin.jpg", document.baseURI).href;

  bestElement.textContent = String(best);
  modeSelect.value = mode;
  skinSelect.value = skin;
  soundEnabledInput.checked = soundPreferences.enabled;
  soundVolumeInput.value = String(soundPreferences.volume);
  soundVolumeValue.value = `${soundPreferences.volume}%`;
  soundVolumeValue.textContent = `${soundPreferences.volume}%`;
  modeDescription.textContent = modes[mode].description;
  if (isAndroidApp) {
    document.querySelector(".account-panel").hidden = true;
    document.querySelector(".bix-launch-link").hidden = true;
  }
  renderShop();
  showTerminalLine("Ricoins game console ready. Type `help` to see commands.");
  if (!isAndroidApp && authToken) restoreAccount();

  function readShopState() {
    try {
      return normalizeShopState(JSON.parse(localStorage.getItem("flappy-friends-shop") || "{}"));
    } catch {
      return normalizeShopState({});
    }
  }

  function normalizeShopState(saved) {
    const items = saved.items && typeof saved.items === "object" ? saved.items : {};
    const equippedWings = ["basic", "wingsRainbow", "wingsGolden", "wingsDiamond", "wingsRuby", "wingsGod"].includes(saved.equippedWings)
      ? saved.equippedWings
      : "basic";
    const trailIds = shopItems.filter((item) => item.type === "trail").map((item) => item.id);
    const equippedTrail = trailIds.includes(saved.equippedTrail) ? saved.equippedTrail : "none";
    const ownedTrails = Object.fromEntries(trailIds.map((id) => [id, items[id] === true]));
    ownedTrails.trailRainbow = ownedTrails.trailRainbow || items.rainbowTrail === true;
    return {
      wallet: Number.isSafeInteger(saved.wallet) && saved.wallet >= 0 ? saved.wallet : 0,
      equippedWings,
      equippedTrail,
      items: {
        wingsRainbow: items.wingsRainbow === true,
        wingsGolden: items.wingsGolden === true || items.goldenWings === true,
        wingsDiamond: items.wingsDiamond === true,
        wingsRuby: items.wingsRuby === true,
        wingsGod: items.wingsGod === true,
        ...ownedTrails,
        shields: Number.isSafeInteger(items.shields) && items.shields >= 0 ? items.shields : 0
      }
    };
  }

  function saveShopState() {
    localStorage.setItem("flappy-friends-shop", JSON.stringify(shopState));
    queueCloudSave();
  }

  function readSavedObject(key) {
    try {
      const value = JSON.parse(localStorage.getItem(key) || "{}");
      return value && typeof value === "object" && !Array.isArray(value) ? value : {};
    } catch {
      return {};
    }
  }

  function readStoredChoice(key, choices, fallback) {
    try {
      const saved = localStorage.getItem(key);
      return saved && Object.hasOwn(choices, saved) ? saved : fallback;
    } catch {
      return fallback;
    }
  }

  function readStoredToken() {
    try {
      const token = localStorage.getItem("flappy-ricoins-token") || "";
      return /^[A-Za-z0-9_-]{20,128}$/.test(token) ? token : "";
    } catch {
      return "";
    }
  }

  function readInstalledPackages() {
    try {
      const saved = JSON.parse(localStorage.getItem("flappy-ricoins-packages") || "[]");
      return Array.isArray(saved) ? saved.filter((name) => Object.hasOwn(packages, name)) : [];
    } catch {
      return [];
    }
  }

  function readPackageVersions() {
    const saved = readSavedObject("flappy-ricoins-package-versions");
    const versions = {};
    for (const name of Object.keys(packages)) {
      if (typeof saved[name] === "string" && /^\d+\.\d+\.\d+$/.test(saved[name])) {
        versions[name] = saved[name];
      }
    }
    return versions;
  }

  function readSoundPreferences() {
    const saved = readSavedObject("flappy-ricoins-sound");
    return {
      enabled: typeof saved.enabled === "boolean" ? saved.enabled : true,
      volume: Number.isInteger(saved.volume) ? Math.min(100, Math.max(0, saved.volume)) : 45
    };
  }

  function readPackageCatalogVersion() {
    try {
      return localStorage.getItem("flappy-ricoins-catalog") === "2";
    } catch {
      return false;
    }
  }

  function readBestScores() {
    const saved = readSavedObject("flappy-ricoins-bests");
    const scores = {};
    for (const name of Object.keys(modes)) {
      const value = Number(saved[name]);
      if (Number.isSafeInteger(value) && value >= 0) scores[name] = value;
    }
    return scores;
  }

  function normalizeCustomSettings(saved) {
    const normalized = {};
    if (!saved || typeof saved !== "object" || Array.isArray(saved)) return normalized;
    const ranges = {
      gravity: [500, 2400],
      flapStrength: [-750, -200],
      pipeGap: [110, 260],
      pipeSpeed: [80, 420],
      spawnInterval: [0.75, 3]
    };
    for (const [modeName, values] of Object.entries(saved)) {
      if (!Object.hasOwn(modes, modeName) || !values || typeof values !== "object") continue;
      const result = {};
      for (const [key, range] of Object.entries(ranges)) {
        const value = values[key];
        if (typeof value === "number" && Number.isFinite(value) && value >= range[0] && value <= range[1]) {
          result[key] = value;
        }
      }
      if (Object.keys(result).length) normalized[modeName] = result;
    }
    return normalized;
  }

  function normalizeMods(saved) {
    const normalized = {};
    if (!saved || typeof saved !== "object" || Array.isArray(saved)) return normalized;
    for (const [name, mod] of Object.entries(saved).slice(0, 40)) {
      if (!/^[a-z0-9_-]{1,24}$/i.test(name) || !mod || typeof mod !== "object") continue;
      if (!Object.hasOwn(modes, mod.mode) || !Object.hasOwn(skins, mod.skin)) continue;
      normalized[name] = {
        mode: mod.mode,
        skin: mod.skin,
        settings: normalizeCustomSettings({ [mod.mode]: mod.settings })[mod.mode] || {}
      };
    }
    return normalized;
  }

  async function requestApi(path, method = "GET", body, token = authToken) {
    const headers = {};
    if (body !== undefined) headers["Content-Type"] = "application/json";
    if (token) headers.Authorization = `Bearer ${token}`;
    const response = await fetch(`${apiBase}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || `Game service returned ${response.status}.`);
    return result;
  }

  function saveLocalAccountState() {
    try {
      localStorage.setItem("flappy-friends-shop", JSON.stringify(shopState));
      localStorage.setItem("flappy-ricoins-mods", JSON.stringify(mods));
      localStorage.setItem("flappy-ricoins-packages", JSON.stringify(installedPackages));
      localStorage.setItem("flappy-ricoins-package-versions", JSON.stringify(packageVersions));
      localStorage.setItem("flappy-ricoins-catalog", packageCatalogUpdated ? "2" : "1");
      localStorage.setItem("flappy-ricoins-bests", JSON.stringify(bestScores));
      localStorage.setItem("flappy-ricoins-physics", JSON.stringify(customSettings));
      localStorage.setItem("flappy-ricoins-sound", JSON.stringify(soundPreferences));
      localStorage.setItem("flappy-ricoins-mode", mode);
      localStorage.setItem("flappy-ricoins-skin", skin);
    } catch (error) {
      accountStatus.textContent = `This browser could not save game data: ${error.message}`;
    }
  }

  function saveableState() {
    return {
      version: 1,
      shop: shopState,
      mode,
      skin,
      bestScores,
      customSettings,
      mods,
      packages: installedPackages,
      packageVersions,
      packageCatalogUpdated,
      sound: soundPreferences
    };
  }

  function queueCloudSave() {
    saveLocalAccountState();
    if (!authToken) return;
    window.clearTimeout(cloudSaveTimer);
    cloudSaveTimer = window.setTimeout(async () => {
      try {
        await requestApi("/api/state", "PUT", { state: saveableState() });
        accountStatus.textContent = `Signed in as ${accountName}. Your game and mods are saved on this device.`;
      } catch (error) {
        accountStatus.textContent = `Cloud save failed (${error.message}). Your local game is still saved.`;
      }
    }, 350);
  }

  function restoreCloudState(saved) {
    if (!saved || saved.version !== 1) return false;
    if (saved.shop && typeof saved.shop === "object") shopState = normalizeShopState(saved.shop);
    if (Object.hasOwn(modes, saved.mode)) mode = saved.mode;
    if (Object.hasOwn(skins, saved.skin)) skin = saved.skin;
    bestScores = readBestScoresFrom(saved.bestScores);
    customSettings = normalizeCustomSettings(saved.customSettings);
    mods = normalizeMods(saved.mods);
    installedPackages = Array.isArray(saved.packages)
      ? [...new Set(saved.packages.filter((name) => Object.hasOwn(packages, name)))]
      : [];
    packageVersions = normalizePackageVersions(saved.packageVersions, installedPackages);
    packageCatalogUpdated = saved.packageCatalogUpdated === true;
    soundPreferences = normalizeSoundPreferences(saved.sound);
    soundEnabledInput.checked = soundPreferences.enabled;
    soundVolumeInput.value = String(soundPreferences.volume);
    soundVolumeValue.value = `${soundPreferences.volume}%`;
    soundVolumeValue.textContent = `${soundPreferences.volume}%`;
    modeSelect.value = mode;
    skinSelect.value = skin;
    best = readBest(mode);
    modeDescription.textContent = modes[mode].description;
    renderShop();
    updateScoreboard();
    saveLocalAccountState();
    return true;
  }

  function readBestScoresFrom(saved) {
    const result = {};
    if (!saved || typeof saved !== "object") return result;
    for (const name of Object.keys(modes)) {
      const value = saved[name];
      if (Number.isSafeInteger(value) && value >= 0) result[name] = value;
    }
    return result;
  }

  function normalizePackageVersions(saved, installed) {
    const result = {};
    for (const name of installed) {
      const version = saved && saved[name];
      result[name] = typeof version === "string" && /^\d+\.\d+\.\d+$/.test(version)
        ? version
        : packages[name].version;
    }
    return result;
  }

  function normalizeSoundPreferences(saved) {
    return {
      enabled: saved && typeof saved.enabled === "boolean" ? saved.enabled : true,
      volume: saved && Number.isInteger(saved.volume) ? Math.min(100, Math.max(0, saved.volume)) : 45
    };
  }

  async function restoreAccount() {
    try {
      const username = localStorage.getItem("flappy-ricoins-username") || "player";
      accountName = username;
      accountStatus.textContent = `Checking saved game for ${accountName}…`;
      const result = await requestApi("/api/state");
      if (!restoreCloudState(result.state)) {
        await requestApi("/api/state", "PUT", { state: saveableState() });
      }
      accountStatus.textContent = `Signed in as ${accountName}. Your game and mods are saved on this device.`;
      showSignOut(true);
    } catch (error) {
      if (error.message.includes("Sign in to load")) {
        authToken = "";
        try {
          localStorage.removeItem("flappy-ricoins-token");
          localStorage.removeItem("flappy-ricoins-username");
        } catch (storageError) {
          accountStatus.textContent = `The saved login could not be cleared: ${storageError.message}`;
        }
        accountName = "";
      }
      accountStatus.textContent = `Could not load account save (${error.message}). Sign in again or keep playing locally.`;
      showSignOut(false);
    }
  }

  function showSignOut(signedIn) {
    signInButton.hidden = signedIn;
    signUpButton.hidden = signedIn;
    accountForm.hidden = signedIn;
    signOutButton.hidden = !signedIn;
  }

  async function authenticate(action) {
    if (!accountForm.reportValidity()) return;
    signInButton.disabled = true;
    signUpButton.disabled = true;
    accountStatus.textContent = action === "signup" ? "Creating your account…" : "Signing in…";
    try {
      const result = await requestApi(`/api/auth/${action}`, "POST", {
        username: accountUsernameInput.value.trim(),
        password: accountPasswordInput.value
      }, "");
      authToken = result.token;
      accountName = result.username;
      localStorage.setItem("flappy-ricoins-token", authToken);
      localStorage.setItem("flappy-ricoins-username", accountName);
      accountPasswordInput.value = "";
      const saved = await requestApi("/api/state");
      if (!restoreCloudState(saved.state)) {
        await requestApi("/api/state", "PUT", { state: saveableState() });
      }
      showSignOut(true);
      accountStatus.textContent = `Signed in as ${accountName}. Saves and mods are kept with your account.`;
      hintElement.textContent = `Welcome, ${accountName}! Your game save is ready.`;
    } catch (error) {
      accountStatus.textContent = error.message;
    } finally {
      signInButton.disabled = false;
      signUpButton.disabled = false;
    }
  }

  async function signOut() {
    signOutButton.disabled = true;
    try {
      await requestApi("/api/auth/signout", "POST", {});
      window.clearTimeout(cloudSaveTimer);
      authToken = "";
      accountName = "";
      localStorage.removeItem("flappy-ricoins-token");
      localStorage.removeItem("flappy-ricoins-username");
      accountStatus.textContent = "Signed out. This device keeps its local game save.";
      showSignOut(false);
    } catch (error) {
      accountStatus.textContent = `Could not sign out (${error.message}). Check your connection and try again.`;
    } finally {
      signOutButton.disabled = false;
    }
  }

  function modeSettings() {
    const settings = { ...modes[mode] };
    const saved = customSettings[mode] || {};
    for (const key of ["gravity", "flapStrength", "pipeGap", "pipeSpeed", "spawnInterval"]) {
      if (Number.isFinite(saved[key])) settings[key] = saved[key];
    }
    return settings;
  }

  function setMode(name) {
    if (!Object.hasOwn(modes, name)) return false;
    mode = name;
    modeSelect.value = mode;
    best = readBest(mode);
    modeDescription.textContent = modes[mode].description;
    updateScoreboard();
    if (state === "playing") startGame();
    else hintElement.textContent = `${modes[mode].label} mode selected. Click, tap, or press Space to play.`;
    queueCloudSave();
    return true;
  }

  function setSkin(name) {
    const skinName = name.toLowerCase();
    const match = Object.keys(skins).find((candidate) => candidate.toLowerCase() === skinName);
    if (!match) return false;
    skin = match;
    skinSelect.value = skin;
    draw();
    queueCloudSave();
    return true;
  }

  function setSoundEnabled(enabled) {
    soundPreferences.enabled = enabled;
    soundEnabledInput.checked = enabled;
    queueCloudSave();
    if (enabled) playSound("coin");
  }

  function setSoundVolume(value) {
    const volume = Number(value);
    if (!Number.isInteger(volume) || volume < 0 || volume > 100) return false;
    soundPreferences.volume = volume;
    soundVolumeInput.value = String(volume);
    soundVolumeValue.value = `${volume}%`;
    soundVolumeValue.textContent = `${volume}%`;
    queueCloudSave();
    return true;
  }

  function playSound(kind) {
    if (!soundPreferences.enabled || soundPreferences.volume === 0) return;
    const AudioContextType = window.AudioContext || window.webkitAudioContext;
    if (!AudioContextType) return;
    try {
      audioContext ||= new AudioContextType();
      if (audioContext.state === "suspended") audioContext.resume().catch(() => {});
      const now = audioContext.currentTime;
      const settings = {
        flap: [440, 0.075, "triangle"],
        coin: [880, 0.16, "sine"],
        crash: [180, 0.24, "sawtooth"]
      }[kind];
      if (!settings) return;
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      oscillator.type = settings[2];
      oscillator.frequency.setValueAtTime(settings[0], now);
      if (kind === "coin") {
        oscillator.frequency.exponentialRampToValueAtTime(settings[0] * 1.5, now + settings[1] * 0.55);
      } else if (kind === "crash") {
        oscillator.frequency.exponentialRampToValueAtTime(75, now + settings[1]);
      }
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(
        Math.max(0.0002, soundPreferences.volume / 100 * 0.12),
        now + 0.012
      );
      gain.gain.exponentialRampToValueAtTime(0.0001, now + settings[1]);
      oscillator.connect(gain);
      gain.connect(audioContext.destination);
      oscillator.start(now);
      oscillator.stop(now + settings[1] + 0.02);
    } catch (error) {
      hintElement.textContent = `Sound could not play: ${error.message}`;
    }
  }

  function resetGameSettings() {
    soundPreferences = { enabled: true, volume: 45 };
    customSettings = {};
    setMode("classic");
    setSkin("sunny");
    soundEnabledInput.checked = true;
    soundVolumeInput.value = "45";
    soundVolumeValue.value = "45%";
    soundVolumeValue.textContent = "45%";
    queueCloudSave();
    hintElement.textContent = "Game settings reset. Your Ricoins and saved mods are unchanged.";
  }

  function showTerminalLine(text, type = "") {
    const line = document.createElement("p");
    line.className = `terminal-line ${type}`.trim();
    line.textContent = text;
    terminalOutput.append(line);
    while (terminalOutput.children.length > 80) terminalOutput.firstElementChild.remove();
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
  }

  function runTerminalCommand(rawCommand) {
    const command = rawCommand.trim();
    if (!command) return;
    showTerminalLine(`game $ ${command}`, "command");
    let [root, action, ...args] = command.split(/\s+/);
    if (root === "apt" || root === "apt-get") root = "pkg";
    const value = args[0];
    const fail = (message) => showTerminalLine(message, "error");
    const needPackage = (name) => {
      if (installedPackages.includes(name)) return true;
      fail(`This command needs ${name}. Install it with \`pkg install ${name}\`.`);
      return false;
    };

    if (root === "help") {
      showTerminalLine("help | status | mode <classic|chill|speedy|horror|fun|extreme> | skin <sunny|sunset|midnight>");
      showTerminalLine("bird gravity <500-2400> | bird flap <200-750> | world gap <110-260> | world speed <80-420> | world interval <0.75-3>");
      showTerminalLine("settings show | settings sound on|off | settings volume <0-100> | settings reset");
      showTerminalLine("mod save|load|delete <name> | mod list | pkg search|info|list|install|remove|upgrade <name>");
      showTerminalLine("pkg update refreshes the bundled catalog; pkg upgrade updates installed game tools. apt and apt-get aliases also work.");
      showTerminalLine("Install bird-tuner, sky-painter, or flight-lab with `pkg install <name>` to unlock tools.");
      showTerminalLine("Commands only change this game. There is no operating-system shell or arbitrary code execution.");
      return;
    }

    if (root === "clear") {
      terminalOutput.replaceChildren();
      return;
    }

    if (root === "status") {
      const settings = modeSettings();
      showTerminalLine(`Mode ${mode} · world ${skin} · wallet ${shopState.wallet} Ricoins`);
      showTerminalLine(`Bird gravity ${settings.gravity} · flap ${Math.abs(settings.flapStrength)} · gap ${settings.pipeGap} · speed ${settings.pipeSpeed}`);
      showTerminalLine(`Sounds ${soundPreferences.enabled ? "on" : "off"} · volume ${soundPreferences.volume}% · saved mods ${Object.keys(mods).length}`);
      showTerminalLine(`Game tools ${installedPackages.length}/${Object.keys(packages).length} · catalog ${packageCatalogUpdated ? "current" : "needs update"}`);
      return;
    }

    if (root === "settings" && action === "show" && args.length === 0) {
      showTerminalLine(`Sound ${soundPreferences.enabled ? "on" : "off"} · volume ${soundPreferences.volume}% · mode ${mode} · skin ${skin}.`);
      return;
    }

    if (root === "settings" && action === "sound" && args.length === 1 && ["on", "off"].includes(value)) {
      setSoundEnabled(value === "on");
      showTerminalLine(`Game sounds ${value}.`);
      return;
    }

    if (root === "settings" && action === "volume" && args.length === 1) {
      if (!setSoundVolume(Number(value))) return fail("Volume must be a whole number from 0 to 100.");
      showTerminalLine(`Sound volume set to ${soundPreferences.volume}%.`);
      return;
    }

    if (root === "settings" && action === "reset" && args.length === 0) {
      resetGameSettings();
      showTerminalLine("Game settings reset. Your wallet and saved mods were kept.");
      return;
    }

    if (root === "mode" && args.length === 1) {
      if (!setMode(value)) return fail("Unknown mode. Run `help` to see valid modes.");
      showTerminalLine(`Mode set to ${mode}.`);
      return;
    }

    if (root === "skin" && args.length === 1) {
      if (!needPackage("sky-painter")) return;
      if (!setSkin(value)) return fail("Unknown world skin. Choose sunny, sunset, or midnight.");
      showTerminalLine(`World skin set to ${skin}.`);
      return;
    }

    if ((root === "bird" || root === "world") && args.length === 1) {
      if (!needPackage(root === "bird" ? "bird-tuner" : "sky-painter")) return;
      const setting = root === "bird"
        ? { gravity: { key: "gravity", min: 500, max: 2400 }, flap: { key: "flapStrength", min: 200, max: 750 } }[action]
        : { gap: { key: "pipeGap", min: 110, max: 260 }, speed: { key: "pipeSpeed", min: 80, max: 420 }, interval: { key: "spawnInterval", min: 0.75, max: 3 } }[action];
      const number = Number(value);
      if (!setting || !Number.isFinite(number) || number < setting.min || number > setting.max) {
        return fail(`Invalid ${root} setting. Check the allowed range with \`help\`.`);
      }
      customSettings[mode] = { ...(customSettings[mode] || {}), [setting.key]: setting.key === "flapStrength" ? -number : number };
      saveShopState();
      showTerminalLine(`${mode} ${setting.key} set to ${number}.`);
      return;
    }

    if (root === "mod" && action === "list" && args.length === 0) {
      if (!needPackage("flight-lab")) return;
      const names = Object.keys(mods);
      showTerminalLine(names.length ? `Saved mods: ${names.join(", ")}` : "No saved mods. Tune the bird or world, then run `mod save <name>`.");
      return;
    }

    if (root === "mod" && ["save", "load", "delete"].includes(action) && args.length === 1) {
      if (!needPackage("flight-lab")) return;
      const name = value.toLowerCase();
      if (!/^[a-z0-9_-]{1,24}$/.test(name)) return fail("Mod names may use 1–24 letters, numbers, hyphens, or underscores.");
      if (action === "save") {
        mods[name] = { mode, skin, settings: { ...(customSettings[mode] || {}) } };
        mods = normalizeMods(mods);
        queueCloudSave();
        showTerminalLine(`Saved mod "${name}" (${mode}, ${skin}).`);
      } else if (action === "load") {
        const mod = mods[name];
        if (!mod) return fail(`Mod "${name}" was not found. Run \`mod list\`.`);
        customSettings[mod.mode] = { ...mod.settings };
        setMode(mod.mode);
        setSkin(mod.skin);
        queueCloudSave();
        showTerminalLine(`Loaded mod "${name}".`);
      } else {
        if (!Object.hasOwn(mods, name)) return fail(`Mod "${name}" was not found.`);
        delete mods[name];
        queueCloudSave();
        showTerminalLine(`Deleted mod "${name}".`);
      }
      return;
    }

    if (root === "pkg" && action === "list" && args.length === 0) {
      for (const [name, item] of Object.entries(packages)) {
        const installedVersion = packageVersions[name];
        const update = installedVersion && installedVersion !== item.latest ? " · update available" : "";
        showTerminalLine(`${installedVersion ? `[installed ${installedVersion}]` : "[available]"} ${name} ${item.latest}${update} — ${item.description}`);
      }
      return;
    }

    if (root === "pkg" && action === "search" && args.length === 1) {
      const matches = Object.entries(packages).filter(([name, item]) =>
        `${name} ${item.description}`.toLowerCase().includes(value.toLowerCase())
      );
      showTerminalLine(matches.length
        ? matches.map(([name, item]) => `${name} ${item.latest} — ${item.description}`).join("\n")
        : `No bundled game tools matched "${value}".`);
      return;
    }

    if (root === "pkg" && action === "info" && args.length === 1) {
      const item = packages[value];
      if (!item) return fail(`Unknown game tool "${value}". Run \`pkg search <word>\`.`);
      showTerminalLine(`${value} ${item.latest} · ${item.description}`);
      showTerminalLine(packageVersions[value]
        ? `Installed version ${packageVersions[value]}.`
        : "Not installed. Install it with `pkg install`.");
      return;
    }

    if (root === "pkg" && ["install", "remove", "upgrade"].includes(action) && args.length === 1) {
      if (!Object.hasOwn(packages, value)) return fail(`Unknown built-in game tool "${value}". Run \`pkg list\`.`);
      if (action === "install") {
        if (!installedPackages.includes(value)) installedPackages.push(value);
        packageVersions[value] = packages[value].latest;
        showTerminalLine(`${value} ${packageVersions[value]} installed. Its game commands are ready.`);
      } else {
        if (action === "remove") {
          installedPackages = installedPackages.filter((name) => name !== value);
          delete packageVersions[value];
          showTerminalLine(`Removed ${value}.`);
        } else if (!installedPackages.includes(value)) {
          return fail(`${value} is not installed.`);
        } else {
          const previousVersion = packageVersions[value] || packages[value].version;
          packageVersions[value] = packages[value].latest;
          showTerminalLine(previousVersion === packageVersions[value]
            ? `${value} is already up to date (${packageVersions[value]}).`
            : `${value} upgraded from ${previousVersion} to ${packageVersions[value]}.`);
        }
      }
      queueCloudSave();
      return;
    }

    if (root === "pkg" && action === "update" && args.length === 0) {
      packageCatalogUpdated = true;
      queueCloudSave();
      showTerminalLine("Bundled game tool catalog v2 is ready. Run `pkg upgrade` to update installed tools.");
      return;
    }

    if (root === "pkg" && action === "upgrade" && args.length === 0) {
      if (!packageCatalogUpdated) return fail("Run `pkg update` first to refresh the bundled catalog.");
      if (!installedPackages.length) return showTerminalLine("No game tools are installed. Run `pkg install <name>` first.");
      for (const name of installedPackages) {
        const previousVersion = packageVersions[name] || packages[name].version;
        packageVersions[name] = packages[name].latest;
        showTerminalLine(previousVersion === packageVersions[name]
          ? `${name} is already up to date (${packageVersions[name]}).`
          : `${name} upgraded from ${previousVersion} to ${packageVersions[name]}.`);
      }
      queueCloudSave();
      return;
    }

    fail("Unknown command or arguments. Type `help` for the game command list.");
  }

  function renderShop() {
    walletElement.textContent = String(shopState.wallet);
    shopItemsElement.replaceChildren();

    for (const item of shopItems) {
      const row = document.createElement("div");
      row.className = "shop-item";
      row.dataset.kind = item.type || "upgrade";
      const copy = document.createElement("div");
      copy.className = "shop-item-copy";
      const name = document.createElement("strong");
      name.textContent = item.name;
      const description = document.createElement("span");
      description.textContent = item.description;
      copy.append(name, description);

      const button = document.createElement("button");
      button.className = "shop-buy";
      button.type = "button";
      const quantity = item.id === "shields" ? shopState.items.shields : 0;
      const owned = item.id === "shields" ? quantity > 0 : shopState.items[item.id] === true;
      if (item.type === "wings" || item.type === "trail") {
        const equipped = item.type === "wings"
          ? shopState.equippedWings === item.id
          : shopState.equippedTrail === item.id;
        button.textContent = equipped ? "Equipped" : owned ? "Equip" : `${item.price} Ricoins`;
        button.disabled = equipped;
        button.setAttribute("aria-label", `${equipped ? "Equipped" : owned ? "Equip" : `Buy for ${item.price} Ricoins`}: ${item.name}`);
        if (item.type === "trail") {
          const swatch = document.createElement("span");
          swatch.className = "trail-swatch";
          swatch.setAttribute("aria-hidden", "true");
          swatch.style.background = `linear-gradient(135deg, ${item.colors.join(", ")})`;
          copy.append(swatch);
        }
        button.addEventListener("click", () => owned ? equipShopItem(item) : buyShopItem(item));
      } else {
        button.textContent = owned ? `${item.ownedLabel}${item.id === "shields" ? ` (${quantity})` : ""}` : `${item.price} Ricoins`;
        button.disabled = item.id !== "shields" && owned;
        button.addEventListener("click", () => buyShopItem(item));
      }
      row.append(copy, button);
      shopItemsElement.append(row);
    }
  }

  function equipShopItem(item) {
    if (!shopState.items[item.id]) return;
    const previousWings = shopState.equippedWings;
    const previousTrail = shopState.equippedTrail;
    if (item.type === "wings") shopState.equippedWings = item.id;
    else shopState.equippedTrail = item.id;
    try {
      saveShopState();
    } catch {
      shopState.equippedWings = previousWings;
      shopState.equippedTrail = previousTrail;
      hintElement.textContent = "Your style choice could not be saved in this browser.";
      return;
    }
    renderShop();
    hintElement.textContent = `${item.name} equipped for Ritoma!`;
  }

  function buyShopItem(item) {
    if ((item.type === "wings" || item.type === "trail") && shopState.items[item.id]) {
      equipShopItem(item);
      return;
    }
    if (item.id !== "shields" && shopState.items[item.id]) return;
    if (shopState.wallet < item.price) {
      hintElement.textContent = `You need ${item.price - shopState.wallet} more Ricoins for ${item.name}.`;
      return;
    }

    const previousState = shopState;
    shopState = {
      wallet: shopState.wallet - item.price,
      equippedWings: item.type === "wings" ? item.id : shopState.equippedWings,
      equippedTrail: item.type === "trail" ? item.id : shopState.equippedTrail,
      items: {
        ...shopState.items,
        [item.id]: item.id === "shields" ? shopState.items.shields + 1 : true
      }
    };
    try {
      saveShopState();
    } catch {
      shopState = previousState;
      hintElement.textContent = "Your purchase could not be saved in this browser.";
      return;
    }

    renderShop();
    hintElement.textContent = item.id === "shields"
      ? `Bubble shield added! You have ${shopState.items.shields}.`
      : item.type === "wings" || item.type === "trail" ? `${item.name} bought and equipped!`
        : `${item.name} unlocked for Ritoma!`;
  }

  function readBest(modeName) {
    if (Number.isSafeInteger(bestScores[modeName]) && bestScores[modeName] >= 0) {
      return bestScores[modeName];
    }
    try {
      const saved = localStorage.getItem(`flappy-friends-best-${modeName}`);
      if (saved !== null) return Number(saved) || 0;
      return modeName === "classic" ? Number(localStorage.getItem("flappy-friends-best")) || 0 : 0;
    } catch {
      return 0;
    }
  }

  function saveBest() {
    try {
      localStorage.setItem(`flappy-friends-best-${mode}`, String(best));
      bestScores[mode] = best;
      localStorage.setItem("flappy-ricoins-bests", JSON.stringify(bestScores));
      queueCloudSave();
    } catch {
      hintElement.textContent = "Nice high score! Scores cannot be saved in this browser.";
    }
  }

  function updateScoreboard() {
    scoreElement.textContent = String(score);
    coinsElement.textContent = String(coinCount);
    bestElement.textContent = String(best);
  }

  function startGame() {
    score = 0;
    coinCount = 0;
    bird.y = 300;
    bird.velocity = 0;
    bird.rotation = 0;
    bird.mouthAngle = 0;
    bird.mouthTimer = 0;
    bird.shieldTimer = 0;
    pipes.length = 0;
    tokens.length = 0;
    trail.length = 0;
    spawnTimer = 0.35;
    elapsed = 0;
    state = "playing";
    hintElement.textContent = "Press Space, click, or tap to flap";
    updateScoreboard();
    flap();
  }

  function flap() {
    if (state === "ready" || state === "over") {
      startGame();
      return;
    }
    if (state === "playing") {
      bird.velocity = modeSettings().flapStrength;
      playSound("flap");
    }
  }

  function addPipe() {
    const gap = modeSettings().pipeGap;
    const minCenter = Math.max(130, gap / 2 + 45);
    const maxCenter = Math.min(450, height - 33 - gap / 2 - 45);
    const gapCenter = minCenter + Math.random() * (maxCenter - minCenter);
    const x = width + 18;
    pipes.push({ x, gapCenter, scored: false });
    tokens.push({ x: x + pipeWidth + 32, y: gapCenter + (Math.random() * 76 - 38), collected: false, mouthTriggered: false });
  }

  function endGame() {
    if (shopState.items.shields > 0) {
      shopState.items.shields -= 1;
      bird.shieldTimer = 1.1;
      bird.y = Math.max(bird.radius + 1, Math.min(height - 34 - bird.radius, bird.y));
      bird.velocity = -300;
      playSound("coin");
      try {
        saveShopState();
      } catch {
        hintElement.textContent = "Your shield was used, but its remaining count could not be saved.";
      }
      renderShop();
      hintElement.textContent = "Bubble shield saved Ritoma! Keep flying!";
      return;
    }
    state = "over";
    playSound("crash");
    if (score > best) {
      best = score;
      saveBest();
    }
    updateScoreboard();
    hintElement.textContent = "Game over! Click, tap, or press Space to play again";
  }

  function circleRectCollision(cx, cy, radius, rx, ry, rw, rh) {
    const nearestX = Math.max(rx, Math.min(cx, rx + rw));
    const nearestY = Math.max(ry, Math.min(cy, ry + rh));
    const dx = cx - nearestX;
    const dy = cy - nearestY;
    return dx * dx + dy * dy < radius * radius;
  }

  function update(dt) {
    if (state !== "playing") return;
    const settings = modeSettings();
    elapsed += dt;
    bird.shieldTimer = Math.max(0, bird.shieldTimer - dt);
    bird.velocity += settings.gravity * dt;
    bird.y += bird.velocity * dt;
    bird.rotation = Math.min(1.15, Math.max(-0.45, bird.velocity / 620));
    if (shopState.equippedTrail !== "none") {
      trail.push({ x: bird.x - 16, y: bird.y + 4, age: 0 });
      while (trail.length > 14) trail.shift();
    }
    for (const spark of trail) spark.age += dt;

    spawnTimer -= dt;
    if (spawnTimer <= 0) {
      addPipe();
      spawnTimer = settings.spawnInterval;
    }

    const speed = settings.pipeSpeed + Math.min(score * 2.2, 70);
    for (const pipe of pipes) {
      pipe.x -= speed * dt;
      const topHeight = pipe.gapCenter - settings.pipeGap / 2;
      const bottomY = pipe.gapCenter + settings.pipeGap / 2;
      if (bird.shieldTimer <= 0 && (
        circleRectCollision(bird.x, bird.y, bird.radius - 3, pipe.x, 0, pipeWidth, topHeight) ||
        circleRectCollision(bird.x, bird.y, bird.radius - 3, pipe.x, bottomY, pipeWidth, height - bottomY)
      )) {
        endGame();
        return;
      }
      if (!pipe.scored && pipe.x + pipeWidth < bird.x) {
        pipe.scored = true;
        score += 1;
        updateScoreboard();
      }
    }
    bird.mouthTimer = Math.max(0, bird.mouthTimer - dt);
    let mouthShouldOpen = bird.mouthTimer > 0;
    for (const token of tokens) {
      token.x -= speed * dt;
      const horizontalDistance = token.x - bird.x;
      const distance = Math.hypot(bird.x - token.x, bird.y - token.y);
      if (!token.collected && !token.mouthTriggered && horizontalDistance > -bird.radius - 22
        && horizontalDistance < bird.radius + 76
        && Math.abs(bird.y - token.y) < bird.radius + 54) {
        token.mouthTriggered = true;
      }
      if (!token.collected && token.mouthTriggered && horizontalDistance > -bird.radius - 22) mouthShouldOpen = true;
      if (!token.collected && distance < bird.radius + 22) {
        token.collected = true;
        playSound("coin");
        bird.mouthTimer = 0.28;
        mouthShouldOpen = true;
        const coinReward = mode === "fun" ? 2 : 1;
        coinCount += coinReward;
        score += 2;
        shopState.wallet += coinReward;
        try {
          saveShopState();
        } catch {
          hintElement.textContent = "Ricoins collected, but your wallet could not be saved in this browser.";
        }
        renderShop();
        updateScoreboard();
      }
    }
    const mouthTarget = mouthShouldOpen ? 0.92 : 0;
    bird.mouthAngle += (mouthTarget - bird.mouthAngle) * Math.min(1, dt * 13);

    while (pipes.length && pipes[0].x + pipeWidth < -10) pipes.shift();
    while (tokens.length && tokens[0].x < -40) tokens.shift();

    if (bird.shieldTimer <= 0 && (bird.y - bird.radius < 0 || bird.y + bird.radius > height - 33)) endGame();
  }

  function drawBackground() {
    const colors = skins[skin];
    const sky = ctx.createLinearGradient(0, 0, 0, height);
    sky.addColorStop(0, colors.skyTop);
    sky.addColorStop(1, colors.skyBottom);
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, width, height);

    if (mode === "horror") {
      const shade = ctx.createLinearGradient(0, 0, 0, height);
      shade.addColorStop(0, "#21142c55");
      shade.addColorStop(1, "#120b2677");
      ctx.fillStyle = shade;
      ctx.fillRect(0, 0, width, height);
      ctx.fillStyle = "#e8d4ff";
      for (const [x, y] of [[74, 173], [360, 116], [286, 263]]) {
        ctx.globalAlpha = 0.45 + Math.sin(elapsed * 4 + x) * 0.2;
        ctx.beginPath();
        ctx.arc(x, y, 2.5, 0, Math.PI * 2);
        ctx.arc(x + 7, y, 2.5, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    }

    ctx.fillStyle = colors.clouds;
    for (const cloud of [{ x: 55, y: 115 }, { x: 340, y: 205 }, { x: 215, y: 55 }]) {
      const drift = (elapsed * 10) % (width + 90);
      const x = (cloud.x - drift + width + 90) % (width + 90) - 45;
      ctx.beginPath();
      ctx.arc(x, cloud.y, 19, 0, Math.PI * 2);
      ctx.arc(x + 21, cloud.y - 8, 24, 0, Math.PI * 2);
      ctx.arc(x + 44, cloud.y, 17, 0, Math.PI * 2);
      ctx.fill();
    }

    ctx.fillStyle = colors.hill;
    ctx.beginPath();
    ctx.moveTo(0, height - 95);
    ctx.quadraticCurveTo(120, height - 180, 250, height - 90);
    ctx.quadraticCurveTo(365, height - 165, width, height - 88);
    ctx.lineTo(width, height);
    ctx.lineTo(0, height);
    ctx.fill();
    ctx.fillStyle = colors.ground;
    ctx.fillRect(0, height - 33, width, 33);
    ctx.fillStyle = colors.groundTop;
    ctx.fillRect(0, height - 33, width, 7);
  }

  function drawPipe(pipe) {
    const colors = skins[skin];
    const topHeight = pipe.gapCenter - modeSettings().pipeGap / 2;
    const bottomY = pipe.gapCenter + modeSettings().pipeGap / 2;
    const capHeight = 22;

    const drawBody = (x, y, w, h) => {
      if (h <= 0) return;
      const gradient = ctx.createLinearGradient(x, 0, x + w, 0);
      gradient.addColorStop(0, colors.pipeDark);
      gradient.addColorStop(0.35, colors.pipeLight);
      gradient.addColorStop(1, colors.pipeDark);
      ctx.fillStyle = gradient;
      ctx.strokeStyle = colors.pipeEdge;
      ctx.lineWidth = 3;
      ctx.fillRect(x, y, w, h);
      ctx.strokeRect(x + 1.5, y + 1.5, w - 3, h - 1.5);
      ctx.fillStyle = "#ffffff3b";
      ctx.fillRect(x + 12, y, 7, h);
    };

    drawBody(pipe.x + 5, 0, pipeWidth - 10, topHeight - capHeight);
    drawBody(pipe.x, Math.max(0, topHeight - capHeight), pipeWidth, capHeight);
    drawBody(pipe.x + 5, bottomY + capHeight, pipeWidth - 10, height - 33 - bottomY - capHeight);
    drawBody(pipe.x, bottomY, pipeWidth, capHeight);
  }

  function drawRoundPhoto(image, x, y, radius, mouthAngle = 0, contain = false) {
    const diameter = radius * 2;
    const scale = contain
      ? Math.min(diameter / image.naturalWidth, diameter / image.naturalHeight)
      : Math.max(diameter / image.naturalWidth, diameter / image.naturalHeight);
    const drawWidth = image.naturalWidth * scale;
    const drawHeight = image.naturalHeight * scale;
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, radius, 0, Math.PI * 2);
    if (mouthAngle > 0.015) {
      ctx.moveTo(x, y);
      ctx.lineTo(x + radius * Math.cos(-mouthAngle), y + radius * Math.sin(-mouthAngle));
      ctx.arc(x, y, radius, -mouthAngle, mouthAngle);
      ctx.closePath();
    }
    ctx.clip(mouthAngle > 0.015 ? "evenodd" : "nonzero");
    if (contain) {
      ctx.fillStyle = "#fff";
      ctx.fill();
    }
    ctx.drawImage(image, x - drawWidth / 2, y - drawHeight / 2, drawWidth, drawHeight);
    ctx.restore();
  }

  function drawCoin(token) {
    if (token.collected) return;
    if (coinImage && coinImage.complete && coinImage.naturalWidth) {
      drawRoundPhoto(coinImage, token.x, token.y, 22, 0, true);
    } else {
      ctx.fillStyle = "#fff2af";
      ctx.font = "bold 18px Nunito, sans-serif";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText("$", token.x, token.y + 1);
    }
  }

  function drawWing(side, flap) {
    ctx.save();
    ctx.scale(side, 1);
    ctx.beginPath();
    ctx.moveTo(-12, 1);
    ctx.quadraticCurveTo(-26, -14 - flap, -37, -9 - flap);
    ctx.quadraticCurveTo(-31, -1, -39, 5 + flap);
    ctx.quadraticCurveTo(-26, 13 + flap, -12, 7);
    ctx.closePath();
    const style = shopItems.find((item) => item.id === shopState.equippedWings);
    if (style) {
      const gradient = ctx.createLinearGradient(-38, -8 - flap, -12, 8);
      style.color.forEach((color, index) => gradient.addColorStop(index / (style.color.length - 1), color));
      ctx.fillStyle = gradient;
      ctx.strokeStyle = style.color[style.color.length - 1];
      ctx.lineWidth = 1.5;
    } else {
      ctx.fillStyle = "#fff8";
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.5;
    }
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }

  function drawTrail() {
    if (shopState.equippedTrail === "none") return;
    const style = shopItems.find((item) => item.id === shopState.equippedTrail);
    if (!style || style.type !== "trail") return;
    for (const [index, spark] of trail.entries()) {
      ctx.globalAlpha = Math.max(0, (shopState.equippedTrail === "trailGhost" ? 0.5 : 0.82) - spark.age * 1.5);
      ctx.fillStyle = style.colors[index % style.colors.length];
      ctx.beginPath();
      const radius = shopState.equippedTrail === "trailGhost" ? 4 : 3.5;
      ctx.arc(spark.x, spark.y, Math.max(1, radius - spark.age * 5), 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalAlpha = 1;
  }

  function drawPlayer() {
    ctx.save();
    ctx.translate(bird.x, bird.y);
    ctx.rotate(state === "playing" ? bird.rotation : Math.sin(elapsed * 3) * 0.08);

    if (playerImage.complete && playerImage.naturalWidth) {
      const flap = state === "playing" ? Math.sin(elapsed * 18) * 5 : Math.sin(elapsed * 3) * 2;
      drawWing(-1, flap);
      drawWing(1, flap);
      drawRoundPhoto(playerImage, 0, 0, bird.radius + 3, bird.mouthAngle);
    } else {
      ctx.beginPath();
      ctx.ellipse(0, 0, bird.radius + 1, bird.radius, 0, 0, Math.PI * 2);
      ctx.fillStyle = skins[skin].bird;
      ctx.fill();
      ctx.lineWidth = 2.5;
      ctx.strokeStyle = skins[skin].birdEdge;
      ctx.stroke();

      ctx.fillStyle = "#fff";
      ctx.beginPath();
      ctx.arc(7, -7, 7, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#263b59";
      ctx.beginPath();
      ctx.arc(9, -7, 3, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = skins[skin].beak;
      ctx.beginPath();
      ctx.moveTo(15, 1);
      ctx.lineTo(29, 6);
      ctx.lineTo(15, 11);
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();
  }

  function drawMessage(title, subtitle) {
    ctx.fillStyle = "#203657";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = "900 34px Nunito, sans-serif";
    ctx.fillText(title, width / 2, height * 0.39);
    ctx.font = "700 16px Nunito, sans-serif";
    ctx.fillStyle = "#354d6d";
    ctx.fillText(subtitle, width / 2, height * 0.39 + 36);
  }

  function draw() {
    drawBackground();
    for (const pipe of pipes) drawPipe(pipe);
    for (const token of tokens) drawCoin(token);
    drawTrail();
    drawPlayer();
    if (bird.shieldTimer > 0) {
      ctx.beginPath();
      ctx.arc(bird.x, bird.y, bird.radius + 12, 0, Math.PI * 2);
      ctx.lineWidth = 2;
      ctx.strokeStyle = "#80edffcc";
      ctx.stroke();
    }
    if (state === "ready") {
      drawMessage("Ready to fly?", "Tap or press Space to start");
    } else if (state === "over") {
      drawMessage("Oops! Try again", `Score ${score}  ·  Coins ${coinCount}`);
    }
  }

  function frame(timestamp) {
    const dt = lastTime ? Math.min((timestamp - lastTime) / 1000, 0.035) : 0;
    lastTime = timestamp;
    update(dt);
    draw();
    requestAnimationFrame(frame);
  }

  function loadPhoto(input, target) {
    const file = input.files && input.files[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      hintElement.textContent = "Please choose an image file.";
      input.value = "";
      return;
    }
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      const image = new Image();
      image.addEventListener("load", () => {
        if (target === "player") playerImage = image;
        else coinImage = image;
        hintElement.textContent = target === "player"
          ? "Your picture is now flying with wings!"
          : "Friend's picture added to your coins!";
      });
      image.addEventListener("error", () => {
        hintElement.textContent = "That picture could not be opened. Try another image.";
      });
      image.src = reader.result;
    });
    reader.addEventListener("error", () => {
      hintElement.textContent = "That picture could not be read. Try another image.";
    });
    reader.readAsDataURL(file);
  }

  canvas.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    flap();
  });
  document.addEventListener("keydown", (event) => {
    if (event.target instanceof HTMLElement
      && (event.target.closest(".terminal-form, .account-form") || event.target.isContentEditable)) return;
    if (event.code === "Space" || event.code === "ArrowUp") {
      event.preventDefault();
      flap();
    }
  });
  accountForm.addEventListener("submit", (event) => {
    event.preventDefault();
    authenticate("signin");
  });
  signInButton.addEventListener("click", () => authenticate("signin"));
  signUpButton.addEventListener("click", () => authenticate("signup"));
  signOutButton.addEventListener("click", signOut);
  terminalForm.addEventListener("submit", (event) => {
    event.preventDefault();
    runTerminalCommand(terminalInput.value);
    terminalInput.value = "";
    terminalInput.focus();
  });
  playerInput.addEventListener("change", () => loadPhoto(playerInput, "player"));
  coinInput.addEventListener("change", () => loadPhoto(coinInput, "coin"));
  document.getElementById("reset-photos").addEventListener("click", () => {
    playerImage = new Image();
    coinImage = new Image();
    playerImage.src = new URL("assets/player.jpg", document.baseURI).href;
    coinImage.src = new URL("assets/coin.jpg", document.baseURI).href;
    playerInput.value = "";
    coinInput.value = "";
    hintElement.textContent = "Your game pictures are back.";
  });
  modeSelect.addEventListener("change", () => {
    setMode(modeSelect.value);
  });
  skinSelect.addEventListener("change", () => {
    setSkin(skinSelect.value);
  });
  soundEnabledInput.addEventListener("change", () => setSoundEnabled(soundEnabledInput.checked));
  soundVolumeInput.addEventListener("input", () => setSoundVolume(soundVolumeInput.value));
  resetSettingsButton.addEventListener("click", resetGameSettings);

  let installPrompt;
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    installPrompt = event;
    installButton.hidden = false;
  });
  installButton.addEventListener("click", async () => {
    if (!installPrompt) return;
    await installPrompt.prompt();
    const result = await installPrompt.userChoice;
    installPrompt = null;
    installButton.hidden = true;
    if (result.outcome === "accepted") hintElement.textContent = "Collect Ricoins was installed!";
  });
  window.addEventListener("appinstalled", () => {
    installPrompt = null;
    installButton.hidden = true;
    hintElement.textContent = "Collect Ricoins was installed!";
  });
  if (!isAndroidApp && "serviceWorker" in navigator && window.isSecureContext) {
    navigator.serviceWorker.register("./service-worker.js")
      .catch(() => {
        hintElement.textContent = "Offline app setup failed. Restart the game with start_app.bat.";
      });
  }

  draw();
  requestAnimationFrame(frame);
})();