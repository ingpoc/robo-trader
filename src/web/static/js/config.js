// Configuration page JavaScript
class ConfigManager {
    constructor() {
        this.saveBtn = document.getElementById('saveConfig');
        this.resetBtn = document.getElementById('resetConfig');
        this.exportBtn = document.getElementById('exportConfig');

        this.init();
    }

    init() {
        this.saveBtn.addEventListener('click', () => this.saveConfig());
        this.resetBtn.addEventListener('click', () => this.resetConfig());
        this.exportBtn.addEventListener('click', () => this.exportConfig());

        this.loadCurrentConfig();
    }

    loadCurrentConfig() {
        // Load current configuration from API
        // For now, we'll use default values
    }

    async saveConfig() {
        const config = {
            riskManagement: {
                maxPositionSize: parseFloat(document.getElementById('maxPositionSize').value),
                stopLossPercent: parseFloat(document.getElementById('stopLossPercent').value),
                takeProfitPercent: parseFloat(document.getElementById('takeProfitPercent').value)
            },
            analysisPreferences: {
                analysisDepth: document.getElementById('analysisDepth').value,
                sectorFocus: this.getSelectedSectors()
            },
            aiBehavior: {
                confidenceThreshold: parseFloat(document.getElementById('confidenceThreshold').value),
                autoExecute: document.getElementById('autoExecute').checked,
                notificationLevel: document.getElementById('notificationLevel').value
            }
        };

        try {
            this.saveBtn.innerHTML = '💾 Saving...';
            this.saveBtn.disabled = true;

            // In a real implementation, this would save to API

            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 1000));

            this.showNotification('Configuration saved successfully!', 'success');
            this.saveBtn.innerHTML = '💾 Save Configuration';
            this.saveBtn.disabled = false;

        } catch (error) {
            console.error('Failed to save config:', error);
            this.showNotification('Failed to save configuration', 'error');
            this.saveBtn.innerHTML = '💾 Save Configuration';
            this.saveBtn.disabled = false;
        }
    }

    getSelectedSectors() {
        const checkboxes = document.querySelectorAll('.sector-checkboxes input[type="checkbox"]');
        return Array.from(checkboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.parentElement.textContent.trim());
    }

    resetConfig() {
        if (confirm('Are you sure you want to reset all settings to defaults?')) {
            // Reset to default values
            document.getElementById('maxPositionSize').value = 5;
            document.getElementById('stopLossPercent').value = 15;
            document.getElementById('takeProfitPercent').value = 30;
            document.getElementById('analysisDepth').value = 'medium';
            document.getElementById('confidenceThreshold').value = 65;
            document.getElementById('autoExecute').checked = false;
            document.getElementById('notificationLevel').value = 'high';

            // Reset sector checkboxes
            const checkboxes = document.querySelectorAll('.sector-checkboxes input[type="checkbox"]');
            const defaultSectors = ['Banking', 'IT', 'Energy', 'Healthcare', 'Consumer'];
            checkboxes.forEach(cb => {
                cb.checked = defaultSectors.includes(cb.parentElement.textContent.trim());
            });

            this.showNotification('Configuration reset to defaults', 'info');
        }
    }

    exportConfig() {
        const config = {
            riskManagement: {
                maxPositionSize: document.getElementById('maxPositionSize').value,
                stopLossPercent: document.getElementById('stopLossPercent').value,
                takeProfitPercent: document.getElementById('takeProfitPercent').value
            },
            analysisPreferences: {
                analysisDepth: document.getElementById('analysisDepth').value,
                sectorFocus: this.getSelectedSectors()
            },
            aiBehavior: {
                confidenceThreshold: document.getElementById('confidenceThreshold').value,
                autoExecute: document.getElementById('autoExecute').checked,
                notificationLevel: document.getElementById('notificationLevel').value
            },
            exportDate: new Date().toISOString()
        };

        const dataStr = JSON.stringify(config, null, 2);
        const dataBlob = new Blob([dataStr], {type: 'application/json'});

        const link = document.createElement('a');
        link.href = URL.createObjectURL(dataBlob);
        link.download = `robo-trader-config-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

        this.showNotification('Configuration exported successfully!', 'success');
    }

    showNotification(message, type) {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;

        // Add to page
        document.body.appendChild(notification);

        // Remove after 3 seconds
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 3000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ConfigManager();
});