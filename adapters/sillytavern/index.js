/**
 * Memory Keeper Extension for SillyTavern
 *
 * Provides persistent, coherent character state management
 * for roleplay chats through integration with Memory Keeper API.
 */

const DEFAULT_SETTINGS = {
  serverUrl: "http://localhost:8000",
  autoSync: true,
  extractFacts: true,
  detectDrift: true,
  injectContext: true,
  maxContextLength: 2000,
};

let extensionSettings = { ...DEFAULT_SETTINGS };

// Track current session and characters
let currentSession = null;
let sessionCharacters = {};
let driftAlerts = [];
let panelOpen = false;
let backendHealthy = false;

// ─── Settings Persistence ───────────────────────────────────

/**
 * Load extension settings from SillyTavern's settings system.
 * Restores defaults for any missing keys.
 */
function loadSettings() {
  if (window.extension_settings && window.extension_settings["memory-keeper"]) {
    const saved = window.extension_settings["memory-keeper"];
    extensionSettings.serverUrl =
      typeof saved.server_url === "string" && saved.server_url.length > 0
        ? saved.server_url
        : DEFAULT_SETTINGS.serverUrl;
    extensionSettings.autoSync =
      typeof saved.auto_sync === "boolean"
        ? saved.auto_sync
        : DEFAULT_SETTINGS.autoSync;
    extensionSettings.extractFacts =
      typeof saved.extract_facts === "boolean"
        ? saved.extract_facts
        : DEFAULT_SETTINGS.extractFacts;
    extensionSettings.detectDrift =
      typeof saved.detect_drift === "boolean"
        ? saved.detect_drift
        : DEFAULT_SETTINGS.detectDrift;
    extensionSettings.injectContext =
      typeof saved.inject_context === "boolean"
        ? saved.inject_context
        : DEFAULT_SETTINGS.injectContext;
    extensionSettings.maxContextLength =
      typeof saved.max_context_length === "number" && saved.max_context_length > 0
        ? saved.max_context_length
        : DEFAULT_SETTINGS.maxContextLength;
  } else {
    // First load — initialize the settings object so save works
    if (window.extension_settings) {
      window.extension_settings["memory-keeper"] = {};
    }
    extensionSettings = { ...DEFAULT_SETTINGS };
  }
  console.log("[Memory Keeper] Loaded settings:", extensionSettings);
}

/**
 * Persist current extensionSettings into SillyTavern's settings store.
 */
function saveSettings() {
  if (!window.extension_settings) {
    console.warn("[Memory Keeper] extension_settings not available; cannot save.");
    return;
  }

  window.extension_settings["memory-keeper"] = {
    server_url: extensionSettings.serverUrl,
    auto_sync: extensionSettings.autoSync,
    extract_facts: extensionSettings.extractFacts,
    detect_drift: extensionSettings.detectDrift,
    inject_context: extensionSettings.injectContext,
    max_context_length: extensionSettings.maxContextLength,
    // Persist session data for restoration across reloads
    current_session: currentSession,
    session_characters: sessionCharacters,
  };

  // Use SillyTavern's debounced save if available
  if (typeof window.saveSettingsDebounced === "function") {
    window.saveSettingsDebounced();
  }
}

// ─── Session Persistence ────────────────────────────────────

/**
 * Restore a previously active session from extension_settings.
 * Called during init so we do not create duplicate sessions on every reload.
 */
async function restoreSession() {
  if (!window.extension_settings || !window.extension_settings["memory-keeper"]) {
    return;
  }

  const saved = window.extension_settings["memory-keeper"];
  const savedSessionId = saved.current_session;
  const savedCharacters = saved.session_characters;

  if (!savedSessionId || typeof savedSessionId !== "string") {
    return;
  }

  // Verify the session still exists on the backend by fetching its facts
  // (a lightweight check — any valid endpoint that 404s on unknown sessions works)
  const checkUrl = `${extensionSettings.serverUrl}/sessions/${savedSessionId}/facts`;
  try {
    const response = await fetch(checkUrl);
    if (response.ok) {
      currentSession = savedSessionId;
      sessionCharacters =
        savedCharacters && typeof savedCharacters === "object"
          ? { ...savedCharacters }
          : {};
      console.log(
        `[Memory Keeper] Restored session ${currentSession} with characters:`,
        Object.keys(sessionCharacters),
      );
    } else {
      console.log(
        `[Memory Keeper] Previous session ${savedSessionId} no longer exists on backend; will create new session when needed.`,
      );
    }
  } catch {
    console.warn(
      "[Memory Keeper] Could not verify previous session (backend unreachable); will retry later.",
    );
  }
}

/**
 * Persist the current session ID and characters map to extension_settings.
 */
function persistSession() {
  saveSettings();
}

// ─── Error Handling ─────────────────────────────────────────

/**
 * Show a toast notification using SillyTavern's toastr or fallback to console.
 */
function showToast(message, title, level) {
  if (window.toastr && typeof window.toastr[level] === "function") {
    window.toastr[level](message, title);
  } else {
    const fn =
      level === "error"
        ? console.error
        : level === "warning"
          ? console.warn
          : console.info;
    fn(`[Memory Keeper] ${title || ""}: ${message}`);
  }
}

/**
 * Wrapper for API calls that catches network and HTTP errors,
 * shows a toast, and returns null on failure instead of crashing.
 *
 * @param {Function} fn - An async function that performs the API call.
 * @param {string} fallbackMsg - Human-readable description shown on error.
 * @returns {*} The return value of fn, or null on failure.
 */
async function apiCall(fn, fallbackMsg) {
  try {
    return await fn();
  } catch (error) {
    // Network errors (fetch throws TypeError for network failures)
    if (error instanceof TypeError && error.message.includes("fetch")) {
      showToast(
        `Network error: Could not reach the Memory Keeper backend. Is it running?`,
        fallbackMsg,
        "error",
      );
      console.error(`[Memory Keeper] Network error during "${fallbackMsg}":`, error);
      return null;
    }

    // HTTP errors we threw ourselves or unexpected errors
    const detail =
      error && error.message ? error.message : "Unknown error";
    showToast(detail, fallbackMsg, "error");
    console.error(`[Memory Keeper] Error during "${fallbackMsg}":`, error);
    return null;
  }
}

// ─── Backend Health Check ───────────────────────────────────

/**
 * Check if the Memory Keeper backend is reachable.
 * Updates `backendHealthy` and shows a warning toast if unreachable.
 * Returns true if healthy.
 */
async function checkBackendHealth() {
  try {
    const url = `${extensionSettings.serverUrl}/health`;
    const response = await fetch(url, { signal: AbortSignal.timeout(5000) });
    if (response.ok) {
      backendHealthy = true;
      console.log("[Memory Keeper] Backend is healthy.");
      return true;
    }
    backendHealthy = false;
    showToast(
      `Backend returned HTTP ${response.status}. Some features may not work.`,
      "Memory Keeper",
      "warning",
    );
    return false;
  } catch {
    backendHealthy = false;
    showToast(
      `Cannot reach Memory Keeper backend at ${extensionSettings.serverUrl}. Make sure the server is running.`,
      "Memory Keeper",
      "warning",
    );
    return false;
  }
}

/**
 * Return a small HTML badge showing the current backend status.
 */
function healthStatusHtml() {
  if (backendHealthy) {
    return `<span style="color:#48bb78;font-size:12px;margin-left:8px;" title="Backend connected">&#9679; Connected</span>`;
  }
  return `<span style="color:#f56565;font-size:12px;margin-left:8px;" title="Backend unreachable">&#9679; Disconnected</span>`;
}

// ─── Event Data Validation ──────────────────────────────────

/**
 * Validate that a message event has the expected structure.
 * Returns { message, character } or null if invalid.
 */
function validateMessageEvent(event, eventName) {
  if (!event || !event.detail) {
    console.warn(
      `[Memory Keeper] ${eventName}: event.detail is missing. Event:`,
      event,
    );
    return null;
  }

  const detail = event.detail;

  if (typeof detail.message !== "string" && detail.message !== undefined) {
    console.warn(
      `[Memory Keeper] ${eventName}: event.detail.message is not a string. Got:`,
      typeof detail.message,
    );
  }

  if (typeof detail.character !== "string" && detail.character !== undefined) {
    console.warn(
      `[Memory Keeper] ${eventName}: event.detail.character is not a string. Got:`,
      typeof detail.character,
    );
  }

  const message =
    typeof detail.message === "string" ? detail.message : String(detail.message || "");
  const character =
    typeof detail.character === "string"
      ? detail.character
      : String(detail.character || "Unknown");

  if (!message) {
    console.warn(
      `[Memory Keeper] ${eventName}: empty message content; skipping sync.`,
    );
    return null;
  }

  return { message, character };
}

// ─── Initialization ─────────────────────────────────────────

/**
 * Initialize the extension
 */
async function initExtension() {
  console.log("[Memory Keeper] Initializing extension...");

  loadSettings();

  // Health check first so we know if the backend is up
  await checkBackendHealth();

  // Restore any previously active session
  await restoreSession();

  hookMessageEvents();
  createUIElements();
  createSettingsUI();

  console.log("[Memory Keeper] Extension initialized");
}

// ─── Settings UI ────────────────────────────────────────────

/**
 * Create an HTML settings form and insert it into SillyTavern's
 * extension settings panel.
 */
function createSettingsUI() {
  const settingsHtml = `
    <div id="memory-keeper-settings" class="memory-keeper-settings-container">
      <div class="inline-drawer">
        <div class="inline-drawer-toggle inline-drawer-header">
          <b>Memory Keeper</b>
          <div class="inline-drawer-icon fa-solid fa-circle-chevron-down down"></div>
        </div>
        <div class="inline-drawer-content">

          <div class="memory-keeper-setting-row">
            <label for="mk-server-url">Server URL</label>
            <input
              id="mk-server-url"
              type="text"
              class="text_pole"
              placeholder="http://localhost:8000"
              value="${escapeHtml(extensionSettings.serverUrl)}"
            />
          </div>

          <div class="memory-keeper-setting-row">
            <label class="checkbox_label" for="mk-auto-sync">
              <input id="mk-auto-sync" type="checkbox" ${extensionSettings.autoSync ? "checked" : ""} />
              <span>Auto-sync messages</span>
            </label>
          </div>

          <div class="memory-keeper-setting-row">
            <label class="checkbox_label" for="mk-extract-facts">
              <input id="mk-extract-facts" type="checkbox" ${extensionSettings.extractFacts ? "checked" : ""} />
              <span>Enable fact extraction</span>
            </label>
          </div>

          <div class="memory-keeper-setting-row">
            <label class="checkbox_label" for="mk-detect-drift">
              <input id="mk-detect-drift" type="checkbox" ${extensionSettings.detectDrift ? "checked" : ""} />
              <span>Enable drift detection</span>
            </label>
          </div>

          <div class="memory-keeper-setting-row">
            <label class="checkbox_label" for="mk-inject-context">
              <input id="mk-inject-context" type="checkbox" ${extensionSettings.injectContext ? "checked" : ""} />
              <span>Enable context injection</span>
            </label>
          </div>

          <div class="memory-keeper-setting-row">
            <label for="mk-max-context-length">Max context length (tokens)</label>
            <input
              id="mk-max-context-length"
              type="number"
              class="text_pole"
              min="100"
              max="16000"
              step="100"
              value="${extensionSettings.maxContextLength}"
            />
          </div>

          <div class="memory-keeper-setting-row" style="margin-top:8px;">
            <button id="mk-test-connection" class="menu_button">Test Connection</button>
          </div>

          <div id="mk-settings-status" class="memory-keeper-setting-row" style="font-size:12px;color:#a0aec0;margin-top:4px;"></div>
        </div>
      </div>
    </div>
  `;

  // Insert into SillyTavern's extensions settings panel
  const target = document.getElementById("extensions_settings");
  if (target) {
    const wrapper = document.createElement("div");
    wrapper.innerHTML = settingsHtml;
    target.appendChild(wrapper);
  } else if (typeof $ !== "undefined" && $("#extensions_settings").length) {
    $("#extensions_settings").append(settingsHtml);
  } else {
    // Fallback: try again after a short delay in case DOM is not ready
    console.warn(
      "[Memory Keeper] #extensions_settings not found; settings UI not attached.",
    );
    return;
  }

  // Bind change handlers
  const serverUrlInput = document.getElementById("mk-server-url");
  if (serverUrlInput) {
    serverUrlInput.addEventListener("input", () => {
      extensionSettings.serverUrl = serverUrlInput.value.trim() || DEFAULT_SETTINGS.serverUrl;
      saveSettings();
    });
  }

  const autoSyncCheckbox = document.getElementById("mk-auto-sync");
  if (autoSyncCheckbox) {
    autoSyncCheckbox.addEventListener("change", () => {
      extensionSettings.autoSync = autoSyncCheckbox.checked;
      saveSettings();
    });
  }

  const extractFactsCheckbox = document.getElementById("mk-extract-facts");
  if (extractFactsCheckbox) {
    extractFactsCheckbox.addEventListener("change", () => {
      extensionSettings.extractFacts = extractFactsCheckbox.checked;
      saveSettings();
    });
  }

  const detectDriftCheckbox = document.getElementById("mk-detect-drift");
  if (detectDriftCheckbox) {
    detectDriftCheckbox.addEventListener("change", () => {
      extensionSettings.detectDrift = detectDriftCheckbox.checked;
      saveSettings();
    });
  }

  const injectContextCheckbox = document.getElementById("mk-inject-context");
  if (injectContextCheckbox) {
    injectContextCheckbox.addEventListener("change", () => {
      extensionSettings.injectContext = injectContextCheckbox.checked;
      saveSettings();
    });
  }

  const maxContextInput = document.getElementById("mk-max-context-length");
  if (maxContextInput) {
    maxContextInput.addEventListener("change", () => {
      const val = parseInt(maxContextInput.value, 10);
      extensionSettings.maxContextLength =
        Number.isFinite(val) && val > 0 ? val : DEFAULT_SETTINGS.maxContextLength;
      saveSettings();
    });
  }

  const testBtn = document.getElementById("mk-test-connection");
  if (testBtn) {
    testBtn.addEventListener("click", async () => {
      const statusEl = document.getElementById("mk-settings-status");
      if (statusEl) statusEl.textContent = "Testing connection...";
      const healthy = await checkBackendHealth();
      if (statusEl) {
        statusEl.innerHTML = healthy
          ? '<span style="color:#48bb78;">Connection successful.</span>'
          : `<span style="color:#f56565;">Connection failed. Check that the server is running at ${escapeHtml(extensionSettings.serverUrl)}</span>`;
      }
      // Also update the panel header badge if the panel is open
      updatePanelHealthBadge();
    });
  }
}

// ─── Message Event Hooks ────────────────────────────────────

/**
 * Hook into SillyTavern message events
 */
function hookMessageEvents() {
  if (window.eventSource) {
    window.eventSource.on("message_sent", handleMessageSent);
    window.eventSource.on("message_received", handleMessageReceived);
    window.eventSource.on("character_selected", handleCharacterSelected);
  }
}

/**
 * Handle user message sent event
 */
async function handleMessageSent(event) {
  if (!extensionSettings.autoSync || !currentSession) return;

  const validated = validateMessageEvent(event, "message_sent");
  if (!validated) return;

  await apiCall(
    () => syncMessage(currentSession, validated.character, validated.message),
    "Sync sent message",
  );
}

/**
 * Handle AI message received event
 */
async function handleMessageReceived(event) {
  if (!extensionSettings.autoSync || !currentSession) return;

  const validated = validateMessageEvent(event, "message_received");
  if (!validated) return;

  const { message, character } = validated;

  // Process message through Memory Keeper (extracts facts, relationships, etc.)
  const result = await apiCall(
    () => syncMessage(currentSession, character, message),
    "Sync received message",
  );

  // Check for drift if the message processing returned context
  if (extensionSettings.detectDrift && result) {
    const driftReport = await apiCall(
      () => checkDrift(currentSession, character, message),
      "Check drift",
    );
    if (driftReport && driftReport.inconsistencies_detected) {
      showDriftAlert(character, driftReport);
    }
  }

  // Inject memory context into the next prompt
  if (extensionSettings.injectContext) {
    const context = await apiCall(
      () => getMemoryContext(currentSession, character),
      "Get memory context",
    );
    if (context) {
      injectContext(context);
    }
  }
}

/**
 * Handle character selected event
 */
async function handleCharacterSelected(characterName) {
  try {
    if (!currentSession) {
      const sessionId = await apiCall(
        () => createSession("SillyTavern Session"),
        "Create session",
      );
      if (sessionId) {
        currentSession = sessionId;
        persistSession();
      } else {
        return; // Cannot proceed without a session
      }
    }

    if (!sessionCharacters[characterName]) {
      const charId = await apiCall(
        () => getOrCreateCharacter(currentSession, characterName),
        "Register character",
      );
      if (charId) {
        sessionCharacters[characterName] = charId;
        persistSession();
      }
    }
  } catch (error) {
    console.error("[Memory Keeper] Error selecting character:", error);
  }
}

// ─── API Integration ─────────────────────────────────────────

/**
 * Sync a message to Memory Keeper (the main message processing endpoint)
 */
async function syncMessage(sessionId, character, messageText) {
  const url = `${extensionSettings.serverUrl}/sessions/${sessionId}/messages`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      character_name: character,
      message_content: messageText,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => "");
    throw new Error(
      `Failed to sync message: HTTP ${response.status} ${response.statusText}${errorBody ? " - " + errorBody : ""}`,
    );
  }

  return await response.json();
}

/**
 * Create a new session
 */
async function createSession(sessionName) {
  const url = `${extensionSettings.serverUrl}/sessions`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: sessionName }),
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => "");
    throw new Error(
      `Failed to create session: HTTP ${response.status} ${response.statusText}${errorBody ? " - " + errorBody : ""}`,
    );
  }

  const data = await response.json();
  return data.session_id;
}

/**
 * Get or create character in Memory Keeper
 */
async function getOrCreateCharacter(sessionId, characterName) {
  const url = `${extensionSettings.serverUrl}/sessions/${sessionId}/characters`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name: characterName }),
  });

  if (!response.ok) {
    const errorBody = await response.text().catch(() => "");
    throw new Error(
      `Failed to create character: HTTP ${response.status} ${response.statusText}${errorBody ? " - " + errorBody : ""}`,
    );
  }

  const data = await response.json();
  return data.character_id;
}

/**
 * Check for character drift
 */
async function checkDrift(sessionId, character, messageContent) {
  const url = `${extensionSettings.serverUrl}/sessions/${sessionId}/drift`;

  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      character_name: character,
      message_content: messageContent || "",
    }),
  });

  if (!response.ok) return null;
  return await response.json();
}

/**
 * Get memory context for character
 */
async function getMemoryContext(sessionId, character) {
  const maxLen = extensionSettings.maxContextLength;
  const url = `${extensionSettings.serverUrl}/sessions/${sessionId}/memory?character=${encodeURIComponent(character)}&max_length=${maxLen}`;

  const response = await fetch(url, {
    headers: { Accept: "application/json" },
  });

  if (!response.ok) return null;
  return await response.json();
}

/**
 * List facts for the current session
 */
async function getFacts(sessionId) {
  const url = `${extensionSettings.serverUrl}/sessions/${sessionId}/facts`;
  const response = await fetch(url);
  if (!response.ok) return [];
  return await response.json();
}

/**
 * List relationships for the current session
 */
async function getRelationships(sessionId) {
  const url = `${extensionSettings.serverUrl}/sessions/${sessionId}/relationships`;
  const response = await fetch(url);
  if (!response.ok) return [];
  return await response.json();
}

/**
 * List drift logs for the current session
 */
async function getDriftLogs(sessionId) {
  const url = `${extensionSettings.serverUrl}/sessions/${sessionId}/drift`;
  const response = await fetch(url);
  if (!response.ok) return [];
  return await response.json();
}

/**
 * List snapshots for the current session
 */
async function getSnapshots(sessionId) {
  const url = `${extensionSettings.serverUrl}/sessions/${sessionId}/snapshots`;
  const response = await fetch(url);
  if (!response.ok) return [];
  return await response.json();
}

/**
 * Create a snapshot
 */
async function createSnapshot(sessionId, notes) {
  const url = `${extensionSettings.serverUrl}/sessions/${sessionId}/snapshots`;
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes, created_by: "sillytavern" }),
  });
  if (!response.ok) throw new Error("Failed to create snapshot");
  return await response.json();
}

/**
 * Rollback to a snapshot
 */
async function rollbackToSnapshot(sessionId, snapshotId) {
  const url = `${extensionSettings.serverUrl}/sessions/${sessionId}/rollback/${snapshotId}`;
  const response = await fetch(url, { method: "POST" });
  if (!response.ok) throw new Error("Failed to rollback");
  return await response.json();
}

// ─── Context Injection ───────────────────────────────────────

/**
 * Inject memory context into SillyTavern's system prompt
 */
function injectContext(memoryResponse) {
  if (!memoryResponse || !memoryResponse.context) return;

  // SillyTavern uses window.SillyTavern.getContext() for prompt manipulation
  if (window.SillyTavern && window.SillyTavern.getContext) {
    const ctx = window.SillyTavern.getContext();
    if (ctx && ctx.setExtensionPrompt) {
      ctx.setExtensionPrompt(
        "memory-keeper",
        memoryResponse.context,
        1, // position: after main prompt
        0, // depth: top of extension prompts
      );
      console.log(
        `[Memory Keeper] Injected context (${memoryResponse.facts_count} facts, ${memoryResponse.relationships_count} relationships)`,
      );
    }
  } else {
    console.log("[Memory Keeper] Context ready but SillyTavern API not available");
  }
}

// ─── Drift Alerts ────────────────────────────────────────────

/**
 * Show drift alert notification
 */
function showDriftAlert(character, driftReport) {
  const alert = {
    character,
    timestamp: new Date(),
    report: driftReport,
  };
  driftAlerts.push(alert);

  // Show toast notification if SillyTavern supports it
  if (window.toastr) {
    const severity = driftReport.severity || "minor";
    const msg = `Character drift (${severity}): ${driftReport.overall_assessment}`;
    if (severity === "severe") {
      window.toastr.error(msg, `${character} - Drift Detected`);
    } else if (severity === "moderate") {
      window.toastr.warning(msg, `${character} - Drift Detected`);
    } else {
      window.toastr.info(msg, `${character} - Drift Detected`);
    }
  }

  console.warn(
    `[Memory Keeper] Drift detected for ${character}: ${driftReport.overall_assessment}`,
  );

  // Refresh panel if open
  if (panelOpen) refreshPanel();
}

// ─── UI ──────────────────────────────────────────────────────

/**
 * Create UI elements
 */
function createUIElements() {
  const button = document.createElement("button");
  button.id = "memory-keeper-button";
  button.textContent = "Memory Keeper";
  button.addEventListener("click", toggleMemoryKeeperPanel);

  // Try to attach to SillyTavern's extension area
  const extensionBar =
    document.getElementById("extensionsMenu") ||
    document.getElementById("extensions_settings");
  if (extensionBar) {
    extensionBar.appendChild(button);
  }
}

/**
 * Toggle the Memory Keeper panel
 */
function toggleMemoryKeeperPanel() {
  if (panelOpen) {
    closePanel();
  } else {
    showMemoryKeeperPanel();
  }
}

/**
 * Close the panel
 */
function closePanel() {
  const existing = document.querySelector(".memory-keeper-panel");
  if (existing) existing.remove();
  panelOpen = false;
}

/**
 * Update the health badge in the panel header if the panel is open.
 */
function updatePanelHealthBadge() {
  const badge = document.getElementById("mk-health-badge");
  if (badge) {
    badge.innerHTML = healthStatusHtml();
  }
}

/**
 * Show the Memory Keeper panel with session data
 */
async function showMemoryKeeperPanel() {
  closePanel(); // Remove any existing panel

  const panel = document.createElement("div");
  panel.className = "memory-keeper-panel";

  // Header with health status badge
  panel.innerHTML = `
    <div class="memory-keeper-panel-header">
      <h3 class="memory-keeper-panel-title">
        Memory Keeper
        <span id="mk-health-badge">${healthStatusHtml()}</span>
      </h3>
      <button class="memory-keeper-panel-close" id="mk-close">&times;</button>
    </div>
    <div class="memory-keeper-content" id="mk-content">
      <div class="memory-keeper-loading">
        <div class="spinner"></div>
        <div>Loading memory data...</div>
      </div>
    </div>
  `;

  document.body.appendChild(panel);
  panelOpen = true;

  panel.querySelector("#mk-close").addEventListener("click", closePanel);

  await refreshPanel();
}

/**
 * Refresh the panel content with latest data
 */
async function refreshPanel() {
  const content = document.getElementById("mk-content");
  if (!content || !currentSession) {
    if (content) {
      content.innerHTML = `
        <div class="memory-section">
          <div class="memory-section-title">No Active Session</div>
          <p style="color:#a0aec0;font-size:13px;">Select a character to start a session.</p>
        </div>
      `;
    }
    return;
  }

  try {
    const [facts, relationships, driftLogs, snapshots] = await Promise.all([
      getFacts(currentSession),
      getRelationships(currentSession),
      getDriftLogs(currentSession),
      getSnapshots(currentSession),
    ]);

    let html = "";

    // Session info
    html += `
      <div class="memory-section">
        <div class="memory-section-title">Session</div>
        <div class="memory-item">
          <div class="memory-item-content">
            ID: ${currentSession.substring(0, 8)}...
            <br>Characters: ${Object.keys(sessionCharacters).join(", ") || "None"}
          </div>
        </div>
      </div>
    `;

    // Facts section
    html += `
      <div class="memory-section">
        <div class="memory-section-title">Facts (${facts.length})</div>
        <div class="facts-list">
    `;
    for (const fact of facts.slice(0, 20)) {
      html += `
        <div class="fact-item">
          <span class="fact-subject">${escapeHtml(fact.subject)}</span>
          <span class="fact-predicate">${escapeHtml(fact.predicate)}</span>
          <span class="fact-object">${escapeHtml(fact.object)}</span>
        </div>
      `;
    }
    if (facts.length === 0) {
      html += `<div style="color:#a0aec0;font-size:12px;padding:8px;">No facts extracted yet.</div>`;
    }
    html += `</div></div>`;

    // Relationships section
    html += `
      <div class="memory-section">
        <div class="memory-section-title">Relationships (${relationships.length})</div>
    `;
    for (const rel of relationships) {
      html += `
        <div class="relationship-item">
          <div class="relationship-label">${escapeHtml(rel.label)}</div>
          <div class="relationship-metrics">
            <span>Trust: ${rel.trust_level?.toFixed(1) ?? "?"}</span>
            <span>Power: ${rel.power_balance?.toFixed(1) ?? "?"}</span>
            ${rel.emotional_undercurrent ? `<span>${escapeHtml(rel.emotional_undercurrent)}</span>` : ""}
          </div>
        </div>
      `;
    }
    if (relationships.length === 0) {
      html += `<div style="color:#a0aec0;font-size:12px;padding:8px;">No relationships detected yet.</div>`;
    }
    html += `</div>`;

    // Drift section
    html += `
      <div class="memory-section">
        <div class="memory-section-title">Drift Alerts (${driftLogs.length})</div>
    `;
    for (const drift of driftLogs.slice(0, 10)) {
      const severity = drift.severity || "minor";
      html += `
        <div class="drift-alert drift-severity-${severity}">
          <div class="drift-alert-title">${severity.toUpperCase()} - ${escapeHtml(drift.inconsistency_type || "behavior")}</div>
          <div class="drift-alert-content">${escapeHtml(drift.conflicting_state || "")}</div>
        </div>
      `;
    }
    if (driftLogs.length === 0) {
      html += `<div style="color:#a0aec0;font-size:12px;padding:8px;">No drift detected. Characters are consistent.</div>`;
    }
    html += `</div>`;

    // Snapshots section
    html += `
      <div class="memory-section">
        <div class="memory-section-title">Snapshots (${snapshots.length})</div>
        <button class="memory-button" id="mk-create-snapshot">Create Snapshot</button>
    `;
    for (const snap of snapshots) {
      const date = new Date(snap.timestamp).toLocaleString();
      html += `
        <div class="memory-item" style="margin-top:8px;">
          <div class="memory-item-label">${date}</div>
          <div class="memory-item-content">
            ${escapeHtml(snap.notes || "No notes")}
            <button class="memory-button-secondary" style="margin-top:6px;padding:4px 8px;font-size:11px;width:auto;border:none;border-radius:3px;cursor:pointer;"
              data-snapshot-id="${snap.snapshot_id}">
              Rollback
            </button>
          </div>
        </div>
      `;
    }
    html += `</div>`;

    content.innerHTML = html;

    // Bind snapshot button
    const createBtn = document.getElementById("mk-create-snapshot");
    if (createBtn) {
      createBtn.addEventListener("click", async () => {
        const result = await apiCall(async () => {
          const notes = prompt("Snapshot notes (optional):");
          await createSnapshot(currentSession, notes || "Manual snapshot");
          await refreshPanel();
        }, "Create snapshot");
        // result is undefined on success (void), null on failure — either way we are fine
      });
    }

    // Bind rollback buttons
    content.querySelectorAll("[data-snapshot-id]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const snapshotId = btn.getAttribute("data-snapshot-id");
        if (confirm("Rollback to this snapshot? This cannot be undone.")) {
          const result = await apiCall(async () => {
            await rollbackToSnapshot(currentSession, snapshotId);
            await refreshPanel();
            showToast("Rolled back successfully.", "Memory Keeper", "success");
          }, "Rollback to snapshot");
        }
      });
    });
  } catch (error) {
    content.innerHTML = `
      <div class="memory-section">
        <div class="memory-section-title">Error</div>
        <p style="color:#f56565;font-size:13px;">Failed to load data: ${escapeHtml(error.message)}</p>
      </div>
    `;
  }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Export for SillyTavern
export async function onExtensionLoad() {
  await initExtension();
}
