let ws = null;
let deckState = {};

// Initialize deck positions
function initializeDeck() {
    console.log('initializeDeck called');
    const deckGrid = document.getElementById('deckGrid');
    console.log('deckGrid element:', deckGrid);
    
    if (!deckGrid) {
        console.error('deckGrid element not found!');
        return;
    }
    
    const fragment = document.createDocumentFragment();
    
    for (let i = 1; i <= 9; i++) {
        const position = document.createElement('div');
        position.className = 'deck-position';
        position.id = `position-${i}`;
        position.innerHTML = `
            <div class="position-label">${i}</div>
            <div class="labware empty" id="labware-${i}">Empty</div>
            <div class="volume-indicator" id="volume-${i}">0 μL</div>
        `;
        fragment.appendChild(position);
        
        deckState[i] = {
            labware: 'empty',
            volume: 0,
            active: false
        };
    }
    
    deckGrid.appendChild(fragment);
    console.log('Deck initialized with', deckGrid.children.length, 'positions');
}

// WebSocket connection
function connectWebSocket() {
    try {
        ws = new WebSocket('ws://localhost:8765');
        
        ws.onopen = function() {
            updateConnectionStatus(true);
            addLogEntry('Connected to Bravo server');
        };
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            handleServerMessage(data);
        };
        
        ws.onclose = function() {
            updateConnectionStatus(false);
            addLogEntry('Disconnected from server');
        };
        
        ws.onerror = function() {
            updateConnectionStatus(false);
            addLogEntry('Connection error');
        };
    } catch (error) {
        addLogEntry('Failed to connect: ' + error.message);
    }
}

// Handle messages from server
function handleServerMessage(data) {
    switch (data.type) {
        case 'deck_update':
            updateDeckState(data.deck);
            break;
        case 'operation':
            handleOperation(data);
            break;
        case 'aspirate_operation':
        case 'dispense_operation':
        case 'move_operation':
            showOperationGlow(data.position, data.type);
            break;
    }
}

// Simplified operation glow effect
function showOperationGlow(position, operationType) {
    const positionElement = document.getElementById(`position-${position}`);
    if (positionElement) {
        // Use a single, simple animation class
        positionElement.classList.add('operation-glow');
        
        // Remove the class after animation completes
        setTimeout(() => {
            positionElement.classList.remove('operation-glow');
        }, 1000);
        
        // Log the operation
        const operationNames = {
            'aspirate_operation': 'Aspirating',
            'dispense_operation': 'Dispensing',
            'move_operation': 'Moving to'
        };
        addLogEntry(`${operationNames[operationType]} at position ${position}`);
    }
}

// Update deck state with batching
function updateDeckState(deck) {
    // Batch DOM updates to minimize reflows
    const updates = [];
    
    for (const [position, state] of Object.entries(deck)) {
        const labwareElement = document.getElementById(`labware-${position}`);
        const volumeElement = document.getElementById(`volume-${position}`);
        
        if (labwareElement && volumeElement) {
            updates.push(() => {
                labwareElement.className = `labware ${state.labware}`;
                labwareElement.textContent = state.labware === 'empty' ? 'Empty' : state.labware;
                
                if (state.active) {
                    labwareElement.classList.add('active');
                }
                
                volumeElement.textContent = `${state.volume} μL`;
            });
        }
        
        deckState[position] = state;
    }
    
    // Apply all updates at once
    updates.forEach(update => update());
}

// Handle operations
function handleOperation(data) {
    document.getElementById('currentOperation').textContent = data.operation;
    addLogEntry(`${data.operation}: ${data.details || ''}`);
}

// Utility functions
function updateConnectionStatus(connected) {
    const dot = document.getElementById('connectionDot');
    const text = document.getElementById('connectionText');
    
    if (connected) {
        dot.classList.add('connected');
        text.textContent = 'Connected';
    } else {
        dot.classList.remove('connected');
        text.textContent = 'Disconnected';
    }
}

function addLogEntry(message) {
    const log = document.getElementById('activityLog');
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.textContent = `${new Date().toLocaleTimeString()}: ${message}`;
    log.insertBefore(entry, log.firstChild);
    
    // Keep only last 15 entries to reduce DOM size
    while (log.children.length > 15) {
        log.removeChild(log.lastChild);
    }
}

// Use requestAnimationFrame for timestamp updates
let timestampUpdateId = null;
function updateTimestamp() {
    document.getElementById('timestamp').textContent = new Date().toLocaleTimeString();
    timestampUpdateId = requestAnimationFrame(() => {
        setTimeout(updateTimestamp, 1000);
    });
}

// Demo functions
function simulateTransfer() {
    const fromPos = Math.floor(Math.random() * 9) + 1;
    const toPos = Math.floor(Math.random() * 9) + 1;
    const volume = Math.floor(Math.random() * 500) + 50;
    
    // Show aspirate glow
    showOperationGlow(fromPos, 'aspirate_operation');
    
    // Show dispense glow after a delay
    setTimeout(() => {
        showOperationGlow(toPos, 'dispense_operation');
    }, 600);
    
    addLogEntry(`Simulated transfer: ${volume} μL from position ${fromPos} to ${toPos}`);
}

function clearDeck() {
    for (let i = 1; i <= 9; i++) {
        deckState[i] = { labware: 'empty', volume: 0, active: false };
    }
    updateDeckState(deckState);
    addLogEntry('Deck cleared');
}

function loadDefaultLayout() {
    const defaultLayout = {
        1: { labware: 'tips', volume: 0, active: false },
        2: { labware: 'plate-96', volume: 150000, active: false },
        3: { labware: 'plate-96', volume: 75000, active: false },
        4: { labware: 'reservoir', volume: 500000, active: false },
        5: { labware: 'empty', volume: 0, active: false },
        6: { labware: 'plate-384', volume: 50000, active: false },
        7: { labware: 'empty', volume: 0, active: false },
        8: { labware: 'plate-96', volume: 0, active: false },
        9: { labware: 'tips', volume: 0, active: false }
    };
    updateDeckState(defaultLayout);
    addLogEntry('Default layout loaded');
}

// Initialize on page load - ensure DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing deck...');
    initializeDeck();
    updateTimestamp();
    
    // Load default layout for demo
    setTimeout(() => {
        loadDefaultLayout();
    }, 500);
});

// Fallback initialization if DOMContentLoaded already fired
if (document.readyState === 'loading') {
    // Document is still loading, wait for DOMContentLoaded
} else {
    // Document is already loaded
    console.log('Document already loaded, initializing immediately...');
    initializeDeck();
    updateTimestamp();
    setTimeout(() => {
        loadDefaultLayout();
    }, 500);
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (timestampUpdateId) {
        cancelAnimationFrame(timestampUpdateId);
    }
    if (ws) {
        ws.close();
    }
});