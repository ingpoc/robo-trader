// Logs page JavaScript
class LogsManager {
    constructor() {
        this.logsContainer = document.getElementById('logsDisplay');
        this.logLevelFilter = document.getElementById('logLevel');
        this.refreshBtn = document.getElementById('refreshLogs');
        this.clearBtn = document.getElementById('clearLogs');

        this.init();
    }

    init() {
        this.refreshBtn.addEventListener('click', () => this.refreshLogs());
        this.clearBtn.addEventListener('click', () => this.clearLogs());
        this.logLevelFilter.addEventListener('change', () => this.filterLogs());

        // Auto-refresh every 30 seconds
        setInterval(() => this.refreshLogs(), 30000);

        this.loadLogs();
    }

    async loadLogs() {
        try {
            // In a real implementation, this would fetch from an API
            // For now, we'll simulate some logs
            const mockLogs = [
                {
                    timestamp: new Date().toISOString(),
                    level: 'info',
                    message: 'System initialized successfully'
                },
                {
                    timestamp: new Date(Date.now() - 60000).toISOString(),
                    level: 'success',
                    message: 'Portfolio scan completed: 81 positions updated'
                },
                {
                    timestamp: new Date(Date.now() - 120000).toISOString(),
                    level: 'info',
                    message: 'AI planning task completed for tomorrow'
                },
                {
                    timestamp: new Date(Date.now() - 180000).toISOString(),
                    level: 'warning',
                    message: 'Claude API usage at 95% of weekly limit'
                },
                {
                    timestamp: new Date(Date.now() - 240000).toISOString(),
                    level: 'error',
                    message: 'Failed to connect to broker API - using paper trading mode'
                }
            ];

            this.displayLogs(mockLogs);
        } catch (error) {
            console.error('Failed to load logs:', error);
        }
    }

    displayLogs(logs) {
        this.logsContainer.innerHTML = '';

        logs.forEach(log => {
            const logEntry = document.createElement('div');
            logEntry.className = 'log-entry';

            const timestamp = new Date(log.timestamp).toLocaleString();
            const levelClass = `log-${log.level.toLowerCase()}`;

            logEntry.innerHTML = `
                <span class="log-timestamp">${timestamp}</span>
                <span class="log-level ${levelClass}">${log.level.toUpperCase()}</span>
                <span class="log-message">${log.message}</span>
            `;

            this.logsContainer.appendChild(logEntry);
        });
    }

    filterLogs() {
        const selectedLevel = this.logLevelFilter.value;
        const logEntries = this.logsContainer.querySelectorAll('.log-entry');

        logEntries.forEach(entry => {
            if (selectedLevel === 'all') {
                entry.style.display = 'flex';
            } else {
                const level = entry.querySelector('.log-level').textContent.toLowerCase();
                entry.style.display = level.includes(selectedLevel) ? 'flex' : 'none';
            }
        });
    }

    refreshLogs() {
        this.refreshBtn.innerHTML = '🔄 Refreshing...';
        this.refreshBtn.disabled = true;

        setTimeout(() => {
            this.loadLogs();
            this.refreshBtn.innerHTML = '🔄 Refresh';
            this.refreshBtn.disabled = false;
        }, 1000);
    }

    clearLogs() {
        if (confirm('Are you sure you want to clear all logs?')) {
            this.logsContainer.innerHTML = '<div class="log-entry"><span class="log-message">Logs cleared</span></div>';
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new LogsManager();
});