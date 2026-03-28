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

/**
 * Initialize the extension
 */
async function initExtension() {
  console.log("[Memory Keeper] Initializing extension...");
  
  // Load settings
  loadSettings();
  
  // Hook into message events
  hookMessageEvents();
  
  // Create UI elements
  createUIElements();
  
  console.log("[Memory Keeper] Extension initialized");
}

/**
 * Load extension settings
 */
function loadSettings() {
  // Settings would be loaded from SillyTavern's settings system
  // This is a placeholder for demonstration
  console.log("[Memory Keeper] Loaded settings:", extensionSettings);
}

/**
 * Hook into SillyTavern message events
 */
function hookMessageEvents() {
  // This would hook into SillyTavern's event system
  // Listen for:
  // - Character selected
  // - Message sent/received
  // - Character definition changed
  
  if (window.eventSource) {
    window.eventSource.on("message_sent", handleMessageSent);
    window.eventSource.on("message_received", handleMessageReceived);
    window.eventSource.on("character_selected", handleCharacterSelected);
  }
}

/**
 * Handle message sent event
 */
async function handleMessageSent(event) {
  if (!extensionSettings.autoSync || !currentSession) {
    return;
  }
  
  try {
    const message = event.detail.message;
    const character = event.detail.character;
    
    // Send to Memory Keeper
    await syncMessage(currentSession, character, message);
  } catch (error) {
    console.error("[Memory Keeper] Error syncing message:", error);
  }
}

/**
 * Handle message received event
 */
async function handleMessageReceived(event) {
  if (!extensionSettings.autoSync || !currentSession) {
    return;
  }
  
  try {
    const message = event.detail.message;
    const character = event.detail.character;
    
    // Send to Memory Keeper
    await syncMessage(currentSession, character, message);
    
    // Check for drift
    if (extensionSettings.detectDrift) {
      const driftReport = await checkDrift(currentSession, character);
      if (driftReport && driftReport.inconsistencies_detected) {
        showDriftAlert(character, driftReport);
      }
    }
    
    // Inject context if enabled
    if (extensionSettings.injectContext) {
      const context = await getMemoryContext(currentSession, character);
      injectContext(context);
    }
  } catch (error) {
    console.error("[Memory Keeper] Error processing message:", error);
  }
}

/**
 * Handle character selected event
 */
async function handleCharacterSelected(characterName) {
  try {
    // Create session if needed
    if (!currentSession) {
      currentSession = await createSession("SillyTavern Session");
    }
    
    // Get or create character in Memory Keeper
    if (!sessionCharacters[characterName]) {
      sessionCharacters[characterName] = await getOrCreateCharacter(
        currentSession,
        characterName
      );
    }
  } catch (error) {
    console.error("[Memory Keeper] Error selecting character:", error);
  }
}

/**
 * Sync a message to Memory Keeper
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
async function checkDrift(sessionId, character) {
  const url = `${extensionSettings.serverUrl}/sessions/${sessionId}/drift`;
  
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ character_name: character }),
  });
  
  if (!response.ok) {
    return null;
  }
  
  return await response.json();
}

/**
 * Get memory context for character
 */
async function getMemoryContext(sessionId, character) {
  const url = `${extensionSettings.serverUrl}/sessions/${sessionId}/memory?character=${character}`;
  
  const response = await fetch(url, {
    headers: { "Accept": "application/json" },
  });
  
  if (!response.ok) {
    return null;
  }
  
  return await response.json();
}

/**
 * Inject context into system prompt
 */
function injectContext(context) {
  if (!context) return;
  
  // Inject into SillyTavern's system prompt
  // This would integrate with SillyTavern's API
  console.log("[Memory Keeper] Injecting context:", context);
}

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
  
  // Show notification in UI
  const message = `[Memory Keeper] Character drift detected for ${character}: ${driftReport.overall_assessment}`;
  console.warn(message);
  
  // Could also show in UI toast/modal
}

/**
 * Create UI elements
 */
function createUIElements() {
  // Create button to access Memory Keeper dashboard
  const button = document.createElement("button");
  button.id = "memory-keeper-button";
  button.textContent = "Memory Keeper";
  button.addEventListener("click", showMemoryKeeperPanel);
  
  // Add to SillyTavern UI
  // This would integrate with SillyTavern's UI system
}

/**
 * Show Memory Keeper panel
 */
function showMemoryKeeperPanel() {
  // Create modal/panel showing:
  // - Current session info
  // - Character memory
  // - Detected drift items
  // - Memory snapshots
  // - Rollback options
  console.log("[Memory Keeper] Opening panel...");
}

// Export for SillyTavern
export async function onExtensionLoad() {
  await initExtension();
}
