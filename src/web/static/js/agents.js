/**
 * Agents Control Panel JavaScript
 */

let agentLogs = [];

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    // Add some initial log entries
    logAgentActivity('System', 'Agent control panel initialized');
});

// Run agent
async function runAgent(agentType) {
    const button = event.target;
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Running...';
    button.disabled = true;

    try {
        let response;
        let symbols = '';

        if (agentType === 'technical') {
            symbols = document.getElementById('techSymbols').value || 'INFY,TCS';
        }

        switch (agentType) {
            case 'portfolio':
                response = await fetch('/api/portfolio-scan', { method: 'POST' });
                break;
            case 'technical':
                // For technical analysis, we'd need to call the agent directly
                // For now, simulate with a query
                response = await fetch('/api/market-screening', { method: 'POST' });
                break;
            case 'fundamental':
                response = await fetch('/api/market-screening', { method: 'POST' });
                break;
            case 'monitor':
                // Simulate monitoring
                logAgentActivity('Market Monitor', 'Starting market monitoring...');
                setTimeout(() => {
                    logAgentActivity('Market Monitor', 'Monitoring active - watching for alerts');
                }, 1000);
                resetButton(button, originalText);
                return;
        }

        const result = await response.json();

        if (response.ok) {
            logAgentActivity(getAgentName(agentType), `Completed successfully: ${result.status || 'Done'}`);
            updateLastRun(agentType);
        } else {
            logAgentActivity(getAgentName(agentType), `Error: ${result.error || 'Unknown error'}`, 'error');
        }

    } catch (error) {
        logAgentActivity(getAgentName(agentType), `Network error: ${error.message}`, 'error');
    }

    resetButton(button, originalText);
}

// Get agent display name
function getAgentName(agentType) {
    const names = {
        'portfolio': 'Portfolio Analyzer',
        'technical': 'Technical Analyst',
        'fundamental': 'Fundamental Screener',
        'monitor': 'Market Monitor'
    };
    return names[agentType] || agentType;
}

// Update last run timestamp
function updateLastRun(agentType) {
    const element = document.getElementById(`${agentType}-last-run`);
    if (element) {
        element.textContent = new Date().toLocaleTimeString();
    }
}

// Reset button to original state
function resetButton(button, originalText) {
    button.innerHTML = originalText;
    button.disabled = false;
}

// Log agent activity
function logAgentActivity(agent, message, type = 'info') {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = `[${timestamp}] ${agent}: ${message}`;

    agentLogs.unshift(logEntry);
    if (agentLogs.length > 100) {
        agentLogs.pop(); // Keep only last 100 entries
    }

    updateLogDisplay();

    // Also show as notification for important messages
    if (type === 'error') {
        showNotification(message, 'danger');
    } else if (message.includes('Completed') || message.includes('Started')) {
        showNotification(`${agent}: ${message}`, 'success');
    }
}

// Update log display
function updateLogDisplay() {
    const logContainer = document.getElementById('agentLogs');
    if (!logContainer) return;

    let html = '';
    agentLogs.slice(0, 20).forEach(log => { // Show last 20 entries
        const isError = log.includes('Error') || log.includes('error');
        const classes = isError ? 'text-danger' : 'text-light';
        html += `<div class="${classes}">${log}</div>`;
    });

    if (agentLogs.length === 0) {
        html = '<div class="text-muted">Agent activity will appear here...</div>';
    }

    logContainer.innerHTML = html;
    logContainer.scrollTop = 0; // Scroll to top for new messages
}

// Show notification (reuse from dashboard.js)
function showNotification(message, type) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    document.body.appendChild(notification);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 5000);
}

// Simulate periodic agent activity (for demo)
setInterval(() => {
    // Random agent activity simulation
    const agents = ['Portfolio Analyzer', 'Technical Analyst', 'Risk Manager', 'Market Monitor'];
    const activities = [
        'Checking market conditions...',
        'Analyzing recent trades...',
        'Monitoring risk metrics...',
        'Scanning for opportunities...',
        'Updating indicators...',
        'Validating positions...'
    ];

    const randomAgent = agents[Math.floor(Math.random() * agents.length)];
    const randomActivity = activities[Math.floor(Math.random() * activities.length)];

    // Only log occasionally (10% chance)
    if (Math.random() < 0.1) {
        logAgentActivity(randomAgent, randomActivity);
    }
}, 10000); // Every 10 seconds