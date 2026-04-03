/**
 * Memory Keeper Extension for SillyTavern
 *
 * Provides persistent, coherent character state management
 * for roleplay chats through integration with Memory Keeper API.
 */

let extensionSettings = {
  serverUrl: "http://127.0.0.1:8000",
  autoSync: true,
  extractFacts: true,
  detectDrift: true,
  injectContext: true,
  maxContextLength: 2000,
};

// Track current session and characters
let currentSession = null;
let sessionCharacters = {};
let driftAlerts = [];
let panelOpen = false;

/**
 * Initialize the extension
 */
async function initExtension() {
  console.log("[Memory Keeper] Initializing extension...");

  loadSettings();
  hookMessageEvents();
  createUIElements();

  console.log("[Memory Keeper] Extension initialized");
}

/**
 * Load extension settings from SillyTavern's settings system
 */
function loadSettings() {
  if (window.extension_settings && window.extension_settings["memory-keeper"]) {
    const saved = window.extension_settings["memory-keeper"];
    extensionSettings.serverUrl = saved.server_url || extensionSettings.serverUrl;
    extensionSettings.autoSync = saved.auto_sync ?? extensionSettings.autoSync;
    extensionSettings.extractFacts = saved.extract_facts ?? extensionSettings.extractFacts;
    extensionSettings.detectDrift = saved.detect_drift ?? extensionSettings.detectDrift;
    extensionSettings.injectContext = saved.inject_context ?? extensionSettings.injectContext;
    extensionSettings.maxContextLength = saved.max_context_length || extensionSettings.maxContextLength;
  }
  console.log("[Memory Keeper] Loaded settings:", extensionSettings);
}

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

  try {
    const message = event.detail.message;
    const character = event.detail.character;
    await syncMessage(currentSession, character, message);
  } catch (error) {
    console.error("[Memory Keeper] Error syncing sent message:", error);
  }
}

/**
 * Handle AI message received event
 */
async function handleMessageReceived(event) {
  if (!extensionSettings.autoSync || !currentSession) return;

  try {
    const message = event.detail.message;
    const character = event.detail.character;

    // Process message through Memory Keeper (extracts facts, relationships, etc.)
    const result = await syncMessage(currentSession, character, message);

    // Check for drift if the message processing returned context
    if (extensionSettings.detectDrift && result) {
      const driftReport = await checkDrift(currentSession, character, message);
      if (driftReport && driftReport.inconsistencies_detected) {
        showDriftAlert(character, driftReport);
      }
    }

    // Inject memory context into the next prompt
    if (extensionSettings.injectContext) {
      const context = await getMemoryContext(currentSession, character);
      if (context) {
        injectContext(context);
      }
    }
  } catch (error) {
    console.error("[Memory Keeper] Error processing received message:", error);
  }
}

/**
 * Handle character selected event
 */
async function handleCharacterSelected(characterName) {
  try {
    if (!currentSession) {
      currentSession = await createSession("SillyTavern Session");
    }

    if (!sessionCharacters[characterName]) {
      sessionCharacters[characterName] = await getOrCreateCharacter(
        currentSession,
        characterName,
      );
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
    throw new Error(`Failed to sync message: ${response.statusText}`);
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
    throw new Error(`Failed to create session: ${response.statusText}`);
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
    throw new Error(`Failed to create character: ${response.statusText}`);
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
 * Show the Memory Keeper panel with session data
 */
async function showMemoryKeeperPanel() {
  closePanel(); // Remove any existing panel

  const panel = document.createElement("div");
  panel.className = "memory-keeper-panel";

  // Header
  panel.innerHTML = `
    <div class="memory-keeper-panel-header">
      <h3 class="memory-keeper-panel-title">Memory Keeper</h3>
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
        try {
          const notes = prompt("Snapshot notes (optional):");
          await createSnapshot(currentSession, notes || "Manual snapshot");
          await refreshPanel();
        } catch (e) {
          console.error("[Memory Keeper] Snapshot error:", e);
        }
      });
    }

    // Bind rollback buttons
    content.querySelectorAll("[data-snapshot-id]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const snapshotId = btn.getAttribute("data-snapshot-id");
        if (confirm("Rollback to this snapshot? This cannot be undone.")) {
          try {
            await rollbackToSnapshot(currentSession, snapshotId);
            await refreshPanel();
            if (window.toastr) window.toastr.success("Rolled back successfully.");
          } catch (e) {
            console.error("[Memory Keeper] Rollback error:", e);
            if (window.toastr) window.toastr.error("Rollback failed.");
          }
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
