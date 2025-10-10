/**
 * Agent Controls Component
 *
 * Provides comprehensive control and configuration interface for all trading agents.
 * Allows users to view agent status, configure parameters, and manage agent operations.
 */

class AgentControls {
    constructor() {
        this.agentStatus = {};
        this.agentConfigs = {};
        this.isInitialized = false;
        this.pollingInterval = null;

        this.initialize();
    }

    async initialize() {
        if (this.isInitialized) return;

        this.setupDOM();
        this.setupEventListeners();
        await this.loadAgentStatus();
        await this.loadAgentConfigurations();
        this.startPolling();
        this.isInitialized = true;

        // Agent Controls initialized
    }

    setupDOM() {
        // Check if agent controls already exist
        if (document.getElementById('agentControlsModal')) {
            return;
        }

        // Load the agent controls HTML template
        fetch('/static/templates/components/agent_controls.html')
            .then(response => response.text())
            .then(html => {
                document.body.insertAdjacentHTML('beforeend', html);
                this.bindElements();
            })
            .catch(error => {
                console.error('Failed to load agent controls template:', error);
                this.createFallbackInterface();
            });
    }

    createFallbackInterface() {
        const html = `
            <div class="agent-controls-modal" id="agentControlsModal" style="display: none;">
                <div class="modal-backdrop" onclick="dashboard.hideAgentControls()"></div>
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>🤖 Agent Controls</h3>
                        <button onclick="dashboard.hideAgentControls()">×</button>
                    </div>
                    <div class="modal-body">
                        <div id="agentControls" class="agent-controls">
                            <div class="loading">Loading agent controls...</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', html);
        this.bindElements();
    }

    bindElements() {
        this.modal = document.getElementById('agentControlsModal');
        this.controls = document.getElementById('agentControls');
        this.globalControls = document.getElementById('globalAgentControls');
        this.agentList = document.getElementById('agentList');
    }

    setupEventListeners() {
        if (!this.controls) return;

        // Global control buttons
        if (this.globalControls) {
            const pauseAllBtn = this.globalControls.querySelector('#pauseAllAgents');
            const resumeAllBtn = this.globalControls.querySelector('#resumeAllAgents');
            const resetAllBtn = this.globalControls.querySelector('#resetAllAgents');

            if (pauseAllBtn) pauseAllBtn.addEventListener('click', () => this.pauseAllAgents());
            if (resumeAllBtn) resumeAllBtn.addEventListener('click', () => this.resumeAllAgents());
            if (resetAllBtn) resetAllBtn.addEventListener('click', () => this.resetAllAgents());
        }
    }

    async loadAgentStatus() {
        try {
            const response = await fetch('/api/agents/status');
            const data = await response.json();

            if (response.ok) {
                this.agentStatus = data.agents || {};
                this.updateDisplay();
            } else {
                console.error('Failed to load agent status:', data);
                this.showError('Failed to load agent status');
            }
        } catch (error) {
            console.error('Error loading agent status:', error);
            this.showError('Network error loading agent status');
        }
    }

    async loadAgentConfigurations() {
        try {
            // Load configurations for all agents
            const agentNames = Object.keys(this.agentStatus);
            this.agentConfigs = {};

            for (const agentName of agentNames) {
                try {
                    const response = await fetch(`/api/agents/${agentName}/config`);
                    if (response.ok) {
                        const config = await response.json();
                        this.agentConfigs[agentName] = config;
                    }
                } catch (error) {
                    console.warn(`Failed to load config for ${agentName}:`, error);
                    this.agentConfigs[agentName] = {};
                }
            }
        } catch (error) {
            console.error('Error loading agent configurations:', error);
        }
    }

    updateDisplay() {
        if (!this.controls || !this.agentList) return;

        this.agentList.innerHTML = '';

        Object.entries(this.agentStatus).forEach(([agentName, status]) => {
            const agentElement = this.createAgentControlElement(agentName, status);
            this.agentList.appendChild(agentElement);
        });
    }

    createAgentControlElement(agentName, status) {
        const element = document.createElement('div');
        element.className = 'agent-control-item';
        element.dataset.agent = agentName;

        const config = this.agentConfigs[agentName] || {};
        const isActive = status.active !== false;
        const statusClass = isActive ? 'active' : 'inactive';
        const statusText = isActive ? 'Active' : 'Inactive';

        element.innerHTML = `
            <div class="agent-header">
                <div class="agent-avatar">
                    ${this.getAgentIcon(agentName)}
                </div>
                <div class="agent-info">
                    <h4>${this.formatAgentName(agentName)}</h4>
                    <div class="agent-status ${statusClass}">
                        <span class="status-dot"></span>
                        ${statusText}
                    </div>
                </div>
                <div class="agent-actions">
                    <button class="btn btn-sm btn-outline" onclick="dashboard.configureAgent('${agentName}')">
                        <i class="fas fa-cog"></i>
                    </button>
                    <button class="btn btn-sm ${isActive ? 'btn-warning' : 'btn-success'}"
                            onclick="dashboard.toggleAgent('${agentName}')">
                        <i class="fas fa-${isActive ? 'pause' : 'play'}"></i>
                    </button>
                </div>
            </div>

            <div class="agent-details">
                <div class="agent-stats">
                    <div class="stat">
                        <span class="stat-label">Tools:</span>
                        <span class="stat-value">${status.tools ? status.tools.length : 0}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Last Active:</span>
                        <span class="stat-value">${this.formatLastActive(status.last_active)}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Success Rate:</span>
                        <span class="stat-value">${status.success_rate ? (status.success_rate * 100).toFixed(1) + '%' : 'N/A'}</span>
                    </div>
                </div>

                <div class="agent-tools">
                    <h5>Available Tools:</h5>
                    <div class="tools-list">
                        ${this.renderAgentTools(status.tools || [])}
                    </div>
                </div>

                ${this.renderAgentConfig(agentName, config)}
            </div>
        `;

        return element;
    }

    getAgentIcon(agentName) {
        const icons = {
            'portfolio_analyzer': '📊',
            'technical_analyst': '📈',
            'fundamental_screener': '🔍',
            'risk_manager': '🛡️',
            'execution_agent': '⚡',
            'market_monitor': '📡',
            'educational_agent': '🎓',
            'alert_agent': '🚨',
            'strategy_agent': '🎯'
        };

        // Convert snake_case to expected format
        const normalizedName = agentName.toLowerCase().replace('_', '_');
        return icons[normalizedName] || '🤖';
    }

    formatAgentName(agentName) {
        return agentName
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    formatLastActive(timestamp) {
        if (!timestamp) return 'Never';

        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString();
    }

    renderAgentTools(tools) {
        if (!tools || tools.length === 0) {
            return '<span class="no-tools">No tools available</span>';
        }

        return tools.map(tool => `<span class="tool-tag">${this.formatToolName(tool)}</span>`).join('');
    }

    formatToolName(toolName) {
        // Convert MCP tool names to readable format
        return toolName
            .replace('mcp__agents__', '')
            .replace('mcp__broker__', '')
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }

    renderAgentConfig(agentName, config) {
        if (!config || Object.keys(config).length === 0) {
            return '';
        }

        let configHtml = '<div class="agent-config"><h5>Configuration:</h5>';

        Object.entries(config).forEach(([key, value]) => {
            const displayKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
            const displayValue = this.formatConfigValue(value);

            configHtml += `
                <div class="config-item">
                    <span class="config-key">${displayKey}:</span>
                    <span class="config-value">${displayValue}</span>
                </div>
            `;
        });

        configHtml += '</div>';
        return configHtml;
    }

    formatConfigValue(value) {
        if (typeof value === 'boolean') {
            return value ? 'Enabled' : 'Disabled';
        }
        if (typeof value === 'number') {
            if (value % 1 === 0) return value.toString();
            return value.toFixed(2);
        }
        if (Array.isArray(value)) {
            return value.join(', ');
        }
        return String(value);
    }

    async toggleAgent(agentName) {
        const currentStatus = this.agentStatus[agentName];
        const isActive = currentStatus && currentStatus.active !== false;
        const action = isActive ? 'pause' : 'resume';

        try {
            const response = await fetch(`/api/agents/${agentName}/${action}`, {
                method: 'POST'
            });

            if (response.ok) {
                // Update local status
                this.agentStatus[agentName] = {
                    ...currentStatus,
                    active: !isActive,
                    last_active: new Date().toISOString()
                };

                this.updateDisplay();

                if (window.dashboard && window.dashboard.showToast) {
                    window.dashboard.showToast(
                        `Agent ${this.formatAgentName(agentName)} ${action}d successfully`,
                        'success'
                    );
                }
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error(`Failed to ${action} agent ${agentName}:`, error);
            if (window.dashboard && window.dashboard.showToast) {
                window.dashboard.showToast(`Failed to ${action} agent`, 'error');
            }
        }
    }

    async configureAgent(agentName) {
        const config = this.agentConfigs[agentName] || {};

        // Create configuration modal
        const modal = this.createConfigModal(agentName, config);
        document.body.appendChild(modal);

        // Show modal
        setTimeout(() => modal.classList.add('show'), 100);
    }

    createConfigModal(agentName, config) {
        const modal = document.createElement('div');
        modal.className = 'config-modal';
        modal.innerHTML = `
            <div class="modal-backdrop" onclick="this.closest('.config-modal').remove()"></div>
            <div class="modal-content config-modal-content">
                <div class="modal-header">
                    <h4>Configure ${this.formatAgentName(agentName)}</h4>
                    <button onclick="this.closest('.config-modal').remove()">×</button>
                </div>
                <div class="modal-body">
                    <form id="agentConfigForm">
                        ${this.renderConfigForm(agentName, config)}
                    </form>
                </div>
                <div class="modal-footer">
                    <button type="button" onclick="this.closest('.config-modal').remove()" class="btn btn-secondary">Cancel</button>
                    <button type="button" onclick="window.agentControls.saveAgentConfig('${agentName}')" class="btn btn-primary">Save Changes</button>
                </div>
            </div>
        `;

        return modal;
    }

    renderConfigForm(agentName, config) {
        // This would render appropriate form fields based on agent type
        // For now, provide a basic configuration form
        const formFields = this.getAgentConfigFields(agentName);

        return formFields.map(field => `
            <div class="form-group">
                <label for="${field.key}">${field.label}</label>
                ${this.renderFormField(field, config[field.key])}
                ${field.description ? `<small class="form-help">${field.description}</small>` : ''}
            </div>
        `).join('');
    }

    getAgentConfigFields(agentName) {
        // Define configuration fields for different agent types
        const fieldDefinitions = {
            'risk_manager': [
                { key: 'max_position_size_pct', label: 'Max Position Size (%)', type: 'number', min: 1, max: 20, description: 'Maximum position size as percentage of portfolio' },
                { key: 'max_portfolio_risk_pct', label: 'Max Portfolio Risk (%)', type: 'number', min: 1, max: 10, description: 'Maximum total portfolio risk' },
                { key: 'stop_loss_buffer_pct', label: 'Stop Loss Buffer (%)', type: 'number', min: 0.1, max: 5, description: 'Buffer above stop loss for execution' }
            ],
            'technical_analyst': [
                { key: 'min_confidence_threshold', label: 'Min Confidence Threshold', type: 'number', min: 0.1, max: 1, step: 0.1, description: 'Minimum confidence for signal generation' },
                { key: 'max_signals_per_day', label: 'Max Signals Per Day', type: 'number', min: 1, max: 20, description: 'Maximum trading signals per day' },
                { key: 'preferred_timeframes', label: 'Preferred Timeframes', type: 'multiselect', options: ['1m', '5m', '15m', '1h', '1d'], description: 'Timeframes for analysis' }
            ],
            'fundamental_screener': [
                { key: 'min_market_cap_cr', label: 'Min Market Cap (₹ Cr)', type: 'number', min: 100, description: 'Minimum market capitalization' },
                { key: 'max_debt_equity_ratio', label: 'Max Debt/Equity Ratio', type: 'number', max: 2, step: 0.1, description: 'Maximum acceptable debt-to-equity ratio' },
                { key: 'min_roe_pct', label: 'Min ROE (%)', type: 'number', min: 10, description: 'Minimum return on equity' }
            ]
        };

        return fieldDefinitions[agentName] || [
            { key: 'enabled', label: 'Enabled', type: 'boolean', description: 'Enable or disable this agent' },
            { key: 'log_level', label: 'Log Level', type: 'select', options: ['DEBUG', 'INFO', 'WARNING', 'ERROR'], description: 'Logging verbosity level' }
        ];
    }

    renderFormField(field, currentValue) {
        const value = currentValue !== undefined ? currentValue : field.default;

        switch (field.type) {
            case 'boolean':
                return `<input type="checkbox" id="${field.key}" ${value ? 'checked' : ''}>`;

            case 'number':
                return `<input type="number" id="${field.key}" value="${value || ''}"
                        ${field.min ? `min="${field.min}"` : ''}
                        ${field.max ? `max="${field.max}"` : ''}
                        ${field.step ? `step="${field.step}"` : ''}>`;

            case 'select':
                const options = field.options.map(opt =>
                    `<option value="${opt}" ${opt === value ? 'selected' : ''}>${opt}</option>`
                ).join('');
                return `<select id="${field.key}">${options}</select>`;

            case 'multiselect':
                // Simplified as text input for now
                return `<input type="text" id="${field.key}" value="${Array.isArray(value) ? value.join(', ') : (value || '')}"
                        placeholder="Comma-separated values">`;

            default:
                return `<input type="text" id="${field.key}" value="${value || ''}">`;
        }
    }

    async saveAgentConfig(agentName) {
        const form = document.getElementById('agentConfigForm');
        if (!form) return;

        const formData = new FormData(form);
        const config = {};

        // Collect form data
        for (let [key, value] of formData.entries()) {
            // Convert string values to appropriate types
            if (value === 'on') value = true;
            else if (value === 'off') value = false;
            else if (!isNaN(value) && value !== '') value = Number(value);

            config[key] = value;
        }

        // Handle checkboxes that aren't checked
        const checkboxes = form.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            if (!config[checkbox.id]) {
                config[checkbox.id] = false;
            }
        });

        try {
            const response = await fetch(`/api/agents/${agentName}/configure`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });

            if (response.ok) {
                // Update local config
                this.agentConfigs[agentName] = config;

                // Close modal
                const modal = document.querySelector('.config-modal');
                if (modal) modal.remove();

                if (window.dashboard && window.dashboard.showToast) {
                    window.dashboard.showToast(`Configuration saved for ${this.formatAgentName(agentName)}`, 'success');
                }

                // Refresh display
                this.updateDisplay();
            } else {
                throw new Error(`HTTP ${response.status}`);
            }
        } catch (error) {
            console.error(`Failed to save config for ${agentName}:`, error);
            if (window.dashboard && window.dashboard.showToast) {
                window.dashboard.showToast('Failed to save configuration', 'error');
            }
        }
    }

    async pauseAllAgents() {
        const confirmed = confirm('Pause all agents? They will stop processing new requests.');
        if (!confirmed) return;

        // Implementation would pause all agents
        // This would call an API endpoint to pause all agents
    }

    async resumeAllAgents() {
        // Implementation would resume all agents
        // This would call an API endpoint to resume all agents
    }

    async resetAllAgents() {
        const confirmed = confirm('Reset all agents? This will clear their state and restart them.');
        if (!confirmed) return;

        // Implementation would reset all agents
        // This would call an API endpoint to reset all agents
    }

    showError(message) {
        if (!this.controls) return;

        this.controls.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${message}</p>
                <button onclick="this.loadAgentStatus()">Retry</button>
            </div>
        `;
    }

    startPolling() {
        // Poll for agent status updates every 30 seconds
        this.pollingInterval = setInterval(() => {
            this.loadAgentStatus();
        }, 30000);
    }

    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }

    // Public API methods
    show() {
        if (this.modal) {
            this.modal.style.display = 'flex';
        }
    }

    hide() {
        if (this.modal) {
            this.modal.style.display = 'none';
        }
    }

    // Method called by dashboard to update agent status
    updateAgentStatus(agents) {
        this.agentStatus = agents || {};
        this.updateDisplay();
    }

    refresh() {
        this.loadAgentStatus();
        this.loadAgentConfigurations();
    }

    destroy() {
        this.stopPolling();
        if (this.modal) {
            this.modal.remove();
        }
    }
}

// Immediately create global instance
if (typeof window !== 'undefined') {
    window.AgentControls = AgentControls;
    if (!window.agentControls) {
        window.agentControls = new AgentControls();
    }
}

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AgentControls;
}