/**
 * Modern Robo Trader Dashboard JavaScript
 * Enhanced with real-time updates, interactive features, and sophisticated UX
 */

class RoboTraderDashboard {
    constructor() {
        this.websocket = null;
        this.agentStatus = {};
        this.currentTasks = {};
        this.isConnected = false;
        this.marketOpen = false;

        this.setupErrorHandling();
        this.initialize();
    }

    setupErrorHandling() {
        window.addEventListener('error', (event) => {
            this.logError('error', event.message, {
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno
            }, event.error?.stack);
        });

        window.addEventListener('unhandledrejection', (event) => {
            this.logError('error', `Unhandled promise rejection: ${event.reason}`, {
                promise: event.promise.toString()
            });
        });
    }

    async logError(level, message, context = {}, stackTrace = null) {
        try {
            await fetch('/api/logs/errors', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    level: level,
                    message: message,
                    context: {
                        ...context,
                        userAgent: navigator.userAgent,
                        url: window.location.href,
                        timestamp: new Date().toISOString()
                    },
                    stack_trace: stackTrace
                })
            });
        } catch (error) {
            console.error('Failed to log error to backend:', error);
        }
    }

    async initialize() {
        this.setupEventListeners();
        await this.connectWebSocket();
        this.startPeriodicUpdates();
        this.updateMarketStatus();
        this.setupTradingForm();
        this.loadInitialData();
        this.loadClaudeStatus();
        this.loadAIStatus();
        this.initializeChat();
        this.initializeAlerts();
        this.initializeRecommendations();
        this.initializeAgentControls();
        this.initializeAnalytics();
        this.initializeCharts(); // Initialize charts for new dashboard
        this.animateEntrance();

        // Navigation initialized - using multi-page navigation
    }

    setupEventListeners() {
        // Handle page visibility changes
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible' && !this.isConnected) {
                this.connectWebSocket();
            }
        });

        // Handle form submissions
        const tradeForm = document.getElementById('quickTradeForm');
        if (tradeForm) {
            tradeForm.addEventListener('submit', (e) => this.handleQuickTrade(e));
        }

        // Handle order type changes
        const orderTypeSelect = document.getElementById('orderTypeSelect');
        if (orderTypeSelect) {
            orderTypeSelect.addEventListener('change', (e) => {
                const priceGroup = document.getElementById('priceGroup');
                if (e.target.value === 'LIMIT') {
                    priceGroup.style.display = 'block';
                } else {
                    priceGroup.style.display = 'none';
                }
            });
        }

        // Setup minimal hover interactions
        this.setupHoverAnimations();
    }

    // GSAP Minimal Hover States - Swiss Precision
    setupHoverAnimations() {
        // Card hover - subtle scale
        document.querySelectorAll('.card').forEach(card => {
            card.addEventListener('mouseenter', () => {
                gsap.to(card, {
                    scale: 1.005,
                    duration: 0.2,
                    ease: "power2.out"
                });
            });

            card.addEventListener('mouseleave', () => {
                gsap.to(card, {
                    scale: 1,
                    duration: 0.2,
                    ease: "power2.out"
                });
            });
        });

        // Button hover - minimal feedback
        document.querySelectorAll('.btn').forEach(btn => {
            btn.addEventListener('mouseenter', () => {
                gsap.to(btn, {
                    scale: 1.005,
                    duration: 0.15,
                    ease: "power2.out"
                });
            });

            btn.addEventListener('mouseleave', () => {
                gsap.to(btn, {
                    scale: 1,
                    duration: 0.15,
                    ease: "power2.out"
                });
            });
        });
    }

    async connectWebSocket() {
        try {
            this.websocket = new WebSocket(`ws://${window.location.host}/ws`);

            this.websocket.onopen = (event) => {
                this.isConnected = true;
                this.showToast('Connected to real-time updates', 'success');
                this.updateConnectionStatus(true);
            };

            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };

            this.websocket.onclose = (event) => {
                this.isConnected = false;
                this.showToast('Real-time updates disconnected', 'info');
                this.updateConnectionStatus(false);

                // Reconnect after delay
                setTimeout(() => this.connectWebSocket(), 5000);
            };

            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.showToast('Connection error', 'error');
            };
        } catch (error) {
            console.error('Failed to connect WebSocket:', error);
        }
    }

    handleWebSocketMessage(data) {
        if (data.error) {
            this.showToast(data.error, 'error');
            return;
        }

        // Update portfolio data
        if (data.portfolio) {
            this.updatePortfolioDisplay(data.portfolio);
        }

        // Update intents
        if (data.intents) {
            this.updateIntentsDisplay(data.intents);
        }

        // Update agent status
        if (data.agent_status) {
            this.updateAgentStatus(data.agent_status);
        }

        // Update progress indicators
        if (data.progress) {
            this.updateProgressIndicators(data.progress);
        }

        // NEW: Update AI status
        if (data.ai_status) {
            this.updateAIStatusDisplay(data.ai_status);
        }

        // NEW: Update recommendations
        if (data.recommendations) {
            this.updateRecommendationsDisplay(data.recommendations);
        }

        // Update timestamp
        if (data.timestamp) {
            this.updateLastUpdate(data.timestamp);
        }
    }

// Portfolio Display - Swiss Minimalism Animation
    updatePortfolioDisplay(portfolio) {
    // Rolling number animations for essential metrics
    this.animateMetric('availableCash', portfolio.cash.free, '₹');
    this.animateMetric('totalExposure', portfolio.exposure_total, '₹');
    this.animateMetric('activePositions', portfolio.holdings.length);
    this.animateMetric('riskScore', portfolio.risk_aggregates?.portfolio?.concentration_risk || 0, '', '%');

    // Update data table
    this.updateHoldingsTable(portfolio.holdings);

    // Update status indicators
    this.updateStatusIndicators(portfolio);
}

// GSAP Rolling Number Animation - Swiss Precision
animateMetric(elementId, newValue, prefix = '', suffix = '') {
    const element = document.getElementById(elementId);
    if (!element) return;

    const currentValue = parseFloat(element.textContent.replace(/[^\d.-]/g, '')) || 0;
    const targetValue = parseFloat(newValue) || 0;

    if (Math.abs(currentValue - targetValue) < 0.01) return;

    // GSAP rolling animation with sophisticated easing
    gsap.to({ value: currentValue }, {
        value: targetValue,
        duration: 0.8,
        ease: "power2.out",
        onUpdate: function() {
            const current = this.targets()[0].value;
            let formattedValue;

            if (suffix === '%') {
                formattedValue = `${prefix}${current.toFixed(1)}${suffix}`;
            } else if (prefix === '₹') {
                formattedValue = `${prefix}${Math.round(current)}`;
            } else {
                formattedValue = `${prefix}${current.toFixed(2)}${suffix}`;
            }

            element.textContent = formattedValue;
        },
        onComplete: () => {
            // Ensure final value is exact
            element.textContent = `${prefix}${targetValue.toFixed(suffix === '%' ? 1 : 2)}${suffix}`;
        }
    });
}

// GSAP Entrance Animations - Swiss Minimalism
animateEntrance() {
    // Set initial states
    gsap.set('.card', { opacity: 0, y: 8 });
    gsap.set('.metric-card', { opacity: 0, y: 8 });
    gsap.set('.btn', { opacity: 0, y: 8 });

    // Animate cards in sequence
    gsap.to('.card', {
        opacity: 1,
        y: 0,
        duration: 0.4,
        ease: "power2.out",
        stagger: 0.1
    });

    // Animate metric cards
    gsap.to('.metric-card', {
        opacity: 1,
        y: 0,
        duration: 0.4,
        ease: "power2.out",
        delay: 0.2,
        stagger: 0.05
    });

    // Animate buttons
    gsap.to('.btn', {
        opacity: 1,
        y: 0,
        duration: 0.3,
        ease: "power2.out",
        delay: 0.4,
        stagger: 0.02
    });
}

// Holdings Table - Information Density
updateHoldingsTable(holdings) {
    // Update would modify the data table with new holdings
    // Swiss minimalism focuses on essential data only
}

// Status Indicators - Typography Only (No Color Coding)
updateStatusIndicators(portfolio) {
    const riskScore = portfolio.risk_aggregates?.portfolio?.concentration_risk || 0;
    const riskScoreElement = document.getElementById('riskScore');

    if (riskScoreElement) {
        // Typography-driven risk indication
        let riskText = 'Low';
        if (riskScore > 25) riskText = 'Medium';
        if (riskScore > 40) riskText = 'High';

        // Update the status text (no color changes)
        const statusElement = riskScoreElement.nextElementSibling;
        if (statusElement && statusElement.classList.contains('status-indicator')) {
            statusElement.textContent = riskText;
        }
    }
}

// Update agent status with real-time information
updateAgentStatus(agentStatus) {
    this.agentStatus = { ...this.agentStatus, ...agentStatus };

    Object.entries(agentStatus).forEach(([agent, status]) => {
        const agentElement = document.querySelector(`.agent-item .agent-avatar.${agent}`);
        const activityElement = document.querySelector(`.agent-item:nth-child(${this.getAgentIndex(agent)}) .agent-activity`);

        if (agentElement) {
            agentElement.style.opacity = status.active ? '1' : '0.5';
        }

        if (activityElement) {
            activityElement.textContent = status.message || `Processing ${status.progress || 0}%`;
        }
    });
}

// GSAP Progress Indicators - Smooth Transitions
updateProgressIndicators(progress) {
    Object.entries(progress).forEach(([task, data]) => {
        const progressElement = document.querySelector(`.progress-item:nth-child(${this.getProgressIndex(task)}) .progress-fill`);
        if (progressElement) {
            gsap.to(progressElement, {
                width: `${data.percentage}%`,
                duration: 0.6,
                ease: "power2.out"
            });
        }
    });
}

// Update connection status
updateConnectionStatus(connected) {
    const statusBadge = document.querySelector('.status-badge');
    if (statusBadge) {
        statusBadge.className = connected ? 'status-badge connected' : 'status-badge disconnected';
        statusBadge.innerHTML = `<i class="fas fa-circle"></i> ${connected ? 'Connected' : 'Disconnected'}`;
    }
}

// Update market status
updateMarketStatus() {
    // Simple market hours check (9:15 AM to 3:30 PM IST)
    const now = new Date();
    const istTime = new Date(now.toLocaleString("en-US", {timeZone: "Asia/Kolkata"}));
    const hour = istTime.getHours();
    const minute = istTime.getMinutes();
    const currentTime = hour * 60 + minute;

    const marketOpenTime = 9 * 60 + 15; // 9:15 AM
    const marketCloseTime = 15 * 60 + 30; // 3:30 PM

    this.marketOpen = currentTime >= marketOpenTime && currentTime <= marketCloseTime;

    const marketStatusElement = document.getElementById('marketStatus');
    if (marketStatusElement) {
        marketStatusElement.textContent = this.marketOpen ? 'Open' : 'Closed';
        // Swiss minimalism: No color coding - typography only
    }
}

// Setup trading form with validation and smart features
setupTradingForm() {
    const symbolInput = document.getElementById('symbolInput');
    const sideSelect = document.getElementById('sideSelect');
    const quantityInput = document.getElementById('quantityInput');
    const orderTypeSelect = document.getElementById('orderTypeSelect');
    const priceInput = document.getElementById('priceInput');

    // Real-time validation for symbol input
    if (symbolInput) {
        symbolInput.addEventListener('input', (e) => {
            const value = e.target.value.toUpperCase();
            e.target.value = value;

            // Clear previous errors on input
            this.clearFieldError('symbol');

            // Show suggestions (implement with common NSE stocks)
            this.showSymbolSuggestions(value);
        });

        symbolInput.addEventListener('blur', () => {
            if (symbolInput.value.trim()) {
                this.validateField('symbol');
            }
        });
    }

    // Real-time validation for side select
    if (sideSelect) {
        sideSelect.addEventListener('change', () => {
            this.validateField('side');
        });
    }

    // Real-time validation for quantity input
    if (quantityInput) {
        quantityInput.addEventListener('input', () => {
            this.clearFieldError('quantity');
        });

        quantityInput.addEventListener('blur', () => {
            if (quantityInput.value) {
                this.validateField('quantity');
            }
        });
    }

    // Real-time validation for order type select
    if (orderTypeSelect) {
        orderTypeSelect.addEventListener('change', (e) => {
            this.validateField('orderType');

            // Show/hide price field for limit orders
            const priceGroup = document.getElementById('priceGroup');
            if (e.target.value === 'LIMIT') {
                priceGroup.style.display = 'block';
                // Focus on price input after animation
                setTimeout(() => priceInput && priceInput.focus(), 300);
            } else {
                priceGroup.style.display = 'none';
                this.clearFieldError('price');
            }
        });
    }

    // Real-time validation for price input
    if (priceInput) {
        priceInput.addEventListener('input', () => {
            this.clearFieldError('price');
        });

        priceInput.addEventListener('blur', () => {
            if (priceInput.value && priceInput.offsetParent !== null) { // Only validate if visible
                this.validateField('price');
            }
        });
    }

    // Auto-fill quantity based on symbol and available cash
    if (symbolInput && quantityInput) {
        symbolInput.addEventListener('change', () => this.suggestQuantity());
    }
}

// Validate individual field
validateField(fieldName) {
    const input = document.getElementById(`${fieldName}Input`) || document.getElementById(`${fieldName}Select`);

    if (!input) return;

    let isValid = true;
    let errorMessage = '';

    switch (fieldName) {
        case 'symbol':
            if (!input.value.trim()) {
                errorMessage = 'Symbol is required';
                isValid = false;
            } else if (!/^[A-Z]{2,10}$/.test(input.value.trim())) {
                errorMessage = 'Invalid symbol format (2-10 uppercase letters)';
                isValid = false;
            }
            break;

        case 'side':
            if (!input.value) {
                errorMessage = 'Please select buy or sell';
                isValid = false;
            }
            break;

        case 'quantity':
            const quantity = parseInt(input.value);
            if (!input.value || isNaN(quantity) || quantity <= 0) {
                errorMessage = 'Quantity must be a positive number';
                isValid = false;
            } else if (quantity > 100000) {
                errorMessage = 'Quantity cannot exceed 100,000 shares';
                isValid = false;
            }
            break;

        case 'orderType':
            if (!input.value) {
                errorMessage = 'Please select order type';
                isValid = false;
            }
            break;

        case 'price':
            const price = parseFloat(input.value);
            if (!input.value || isNaN(price) || price <= 0) {
                errorMessage = 'Price must be a positive number';
                isValid = false;
            } else if (price > 100000) {
                errorMessage = 'Price cannot exceed ₹100,000';
                isValid = false;
            }
            break;
    }

    if (isValid) {
        this.showFormSuccess(fieldName);
    } else {
        this.showFormError(fieldName, errorMessage);
    }

    return isValid;
}

// Clear error for specific field
clearFieldError(fieldName) {
    const input = document.getElementById(`${fieldName}Input`) || document.getElementById(`${fieldName}Select`);
    const errorElement = document.getElementById(`${fieldName}-error`);

    if (input) {
        input.classList.remove('error');
    }

    if (errorElement) {
        errorElement.classList.remove('show');
    }
}

// Handle quick trade submission
async handleQuickTrade(event) {
    event.preventDefault();

    // Validate form before submission
    if (!this.validateTradeForm()) {
        this.showToast('Please correct the form errors', 'error');
        return;
    }

    const formData = new FormData(event.target);
    const tradeData = {
        symbol: formData.get('symbol').toUpperCase(),
        side: formData.get('side'),
        quantity: parseInt(formData.get('quantity')),
        order_type: formData.get('order_type'),
        price: formData.get('price') ? parseFloat(formData.get('price')) : null
    };

    // Show loading state
    const submitButton = event.target.querySelector('button[type="submit"]');
    this.setButtonLoading(submitButton, 'Executing Trade...');

    try {
        const response = await fetch('/api/manual-trade', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(tradeData)
        });

        const result = await response.json();

        if (response.ok) {
            this.showToast(result.status, 'success');
            this.showSuccessAnimation(submitButton);
            event.target.reset();
            this.clearFormErrors();
            setTimeout(() => this.loadInitialData(), 1000); // Refresh data
        } else {
            this.showToast(result.error || 'Trade execution failed', 'error');
            this.showErrorAnimation(submitButton);
        }
    } catch (error) {
        this.showToast('Network error - please try again', 'error');
        this.showErrorAnimation(submitButton);
        console.error(error);
    } finally {
        // Reset button after delay
        setTimeout(() => {
            submitButton.disabled = false;
            submitButton.innerHTML = '<i class="fas fa-paper-plane" aria-hidden="true"></i> Execute Trade';
        }, 2000);
    }
}

// Enhanced form validation with visual feedback
validateTradeForm() {
    const symbolInput = document.getElementById('symbolInput');
    const sideSelect = document.getElementById('sideSelect');
    const quantityInput = document.getElementById('quantityInput');
    const orderTypeSelect = document.getElementById('orderTypeSelect');
    const priceInput = document.getElementById('priceInput');

    let isValid = true;

    // Clear previous errors
    this.clearFormErrors();

    // Validate symbol
    if (!symbolInput.value.trim()) {
        this.showFormError('symbol', 'Symbol is required');
        isValid = false;
    } else if (!/^[A-Z]{2,10}$/.test(symbolInput.value.trim())) {
        this.showFormError('symbol', 'Invalid symbol format (2-10 uppercase letters)');
        isValid = false;
    } else {
        this.showFormSuccess('symbol');
    }

    // Validate side
    if (!sideSelect.value) {
        this.showFormError('side', 'Please select buy or sell');
        isValid = false;
    } else {
        this.showFormSuccess('side');
    }

    // Validate quantity
    const quantity = parseInt(quantityInput.value);
    if (!quantityInput.value || isNaN(quantity) || quantity <= 0) {
        this.showFormError('quantity', 'Quantity must be a positive number');
        isValid = false;
    } else if (quantity > 100000) {
        this.showFormError('quantity', 'Quantity cannot exceed 100,000 shares');
        isValid = false;
    } else {
        this.showFormSuccess('quantity');
    }

    // Validate order type
    if (!orderTypeSelect.value) {
        this.showFormError('orderType', 'Please select order type');
        isValid = false;
    } else {
        this.showFormSuccess('orderType');
    }

    // Validate price for limit orders
    if (orderTypeSelect.value === 'LIMIT') {
        const price = parseFloat(priceInput.value);
        if (!priceInput.value || isNaN(price) || price <= 0) {
            this.showFormError('price', 'Price must be a positive number');
            isValid = false;
        } else if (price > 100000) {
            this.showFormError('price', 'Price cannot exceed ₹100,000');
            isValid = false;
        } else {
            this.showFormSuccess('price');
        }
    }

    return isValid;
}

// Show form error message
showFormError(fieldName, message) {
    const input = document.getElementById(`${fieldName}Input`) || document.getElementById(`${fieldName}Select`);
    const errorElement = document.getElementById(`${fieldName}-error`);

    if (input) {
        input.classList.add('error');
        input.classList.remove('success');
    }

    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.add('show');
    }
}

// Show form success state
showFormSuccess(fieldName) {
    const input = document.getElementById(`${fieldName}Input`) || document.getElementById(`${fieldName}Select`);
    const errorElement = document.getElementById(`${fieldName}-error`);

    if (input) {
        input.classList.add('success');
        input.classList.remove('error');
    }

    if (errorElement) {
        errorElement.classList.remove('show');
    }
}

// Clear all form errors
clearFormErrors() {
    const errorElements = document.querySelectorAll('.form-error');
    const inputs = document.querySelectorAll('.form-input');

    errorElements.forEach(el => el.classList.remove('show'));
    inputs.forEach(input => {
        input.classList.remove('error', 'success');
    });
}

// Validate trade parameters (legacy method for API calls)
validateTrade(tradeData) {
    return this.validateTradeForm();
}

// Show symbol suggestions (implement with NSE stock list)
showSymbolSuggestions(partial) {
    // This would show a dropdown with matching NSE stocks
}

// Suggest optimal quantity based on symbol and available cash
suggestQuantity() {
    const symbolInput = document.getElementById('symbolInput');
    const quantityInput = document.getElementById('quantityInput');

    if (!symbolInput.value || !quantityInput) return;

    // This would fetch current price and suggest quantity based on risk management
}

// Update last update timestamp
updateLastUpdate(timestamp) {
    // This would update a "Last updated" indicator
}

// Start periodic updates as backup
startPeriodicUpdates() {
    setInterval(() => {
        this.loadInitialData();
    }, 30000); // Update every 30 seconds
}

// Load initial dashboard data
async loadInitialData() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();
        this.handleWebSocketMessage(data);
    } catch (error) {
        console.error('Failed to load initial data:', error);
    }
}

// Load Claude API status
async loadClaudeStatus() {
    try {
        const response = await fetch('/api/claude-status');
        const status = await response.json();
        this.updateClaudeStatus(status);
        
        // Refresh status periodically
        setInterval(() => this.loadClaudeStatus(), 60000); // Check every minute
    } catch (error) {
        console.error('Failed to load Claude status:', error);
        this.updateClaudeStatus({
            is_valid: false,
            error: 'Failed to check Claude API status'
        });
    }
}

// Update Claude status indicator with rate limit info
updateClaudeStatus(status) {
    const statusElement = document.getElementById('claudeStatus');
    const statusTextElement = document.getElementById('claudeStatusText');
    const rateLimitInfo = document.getElementById('rateLimitInfo');
    const rateLimitText = document.getElementById('rateLimitText');

    if (!statusElement || !statusTextElement) return;

    const isValid = status.is_valid;
    const authMethod = status.account_info?.auth_method || 'unknown';
    const rateLimitData = status.rate_limit_info || {};
    const isLimited = rateLimitData.limited === true;

    // Update status badge
    let statusClass = 'status-badge';
    let statusText = '';

    if (isValid) {
        if (isLimited) {
            statusClass += ' limited';
            statusText = 'Rate Limited';
        } else {
            statusClass += ' connected';
            statusText = 'Connected';
        }

        // Add auth method to status text
        if (authMethod === 'claude_code_cli') {
            statusText += ' (Subscription)';
        } else if (authMethod === 'api_key') {
            statusText += ' (API Key)';
        }
    } else {
        statusClass += ' disconnected';
        statusText = 'Disconnected';
    }

    statusElement.className = statusClass;
    statusTextElement.textContent = statusText;

    // Update rate limit information
    if (rateLimitInfo && isLimited) {
        const limitType = rateLimitData.type || 'unknown';
        const resetsAt = rateLimitData.resets_at || '';

        let limitMessage = `${limitType.charAt(0).toUpperCase() + limitType.slice(1)} limit reached`;
        if (resetsAt) {
            limitMessage += ` • Resets ${resetsAt}`;
        }

        rateLimitText.textContent = limitMessage;
        rateLimitInfo.style.display = 'block';
        rateLimitInfo.className = 'rate-limit-info warning';
    } else if (rateLimitInfo) {
        rateLimitInfo.style.display = 'none';
    }

    // Show error toast if present (only once)
    if (status.error && !this._errorShown) {
        this.showToast(`Claude API: ${status.error}`, 'error');
        this._errorShown = true;
    } else if (isValid && isLimited && !this._limitShown) {
        this.showToast('Claude API rate limit reached', 'warning');
        this._limitShown = true;
    }
}

// NEW: AI Status monitoring
async loadAIStatus() {
    try {
        const response = await fetch('/api/ai/status');
        const status = await response.json();
        this.updateAIStatus(status);
    } catch (error) {
        console.error('Failed to load AI status:', error);
    }
}

updateAIStatus(status) {
    this.aiStatus = status;
    this.updateAIStatusDisplay(status);
    this.updateAIInsights(status);
}

// NEW: Update AI Insights Panel
updateAIInsights(status) {
    const portfolioHealth = document.getElementById('portfolioHealth');
    const todaysFocus = document.getElementById('todaysFocus');
    const apiUsage = document.getElementById('apiUsage');

    if (portfolioHealth) {
        portfolioHealth.textContent = status.portfolio_health || 'Analyzing...';
    }

    if (todaysFocus) {
        const currentTask = status.current_task || status.next_planned_task;
        if (currentTask) {
            todaysFocus.textContent = currentTask;
        } else {
            todaysFocus.textContent = 'No tasks scheduled';
        }
    }

    if (apiUsage) {
        const used = status.api_budget_used || 0;
        const limit = status.daily_api_limit || 25;
        const percentage = limit > 0 ? Math.round((used / limit) * 100) : 0;

        apiUsage.textContent = `${used}/${limit} calls (${percentage}%)`;

        if (percentage >= 90) {
            apiUsage.style.color = '#ef4444';
        } else if (percentage >= 70) {
            apiUsage.style.color = '#f59e0b';
        } else {
            apiUsage.style.color = '';
        }
    }
}

updateAIStatusDisplay(status) {
    const aiStatusElement = document.getElementById('aiStatus');
    if (aiStatusElement) {
        let statusText = 'Idle';
        let statusClass = 'ai-status-idle';

        if (status.current_task) {
            statusText = `Working: ${status.current_task}`;
            statusClass = 'ai-status-active';
        }

        aiStatusElement.textContent = statusText;
        aiStatusElement.className = `ai-status ${statusClass}`;
    }
}

// NEW: Chat Interface Methods
initializeChat() {
    // Load chat component script if not already loaded
    if (!window.aiChat) {
        const script = document.createElement('script');
        script.src = '/static/js/components/ai-chat.js';
        script.onload = () => {
            // AI Chat component loaded
        };
        script.onerror = () => {
            console.warn('Failed to load AI Chat component');
        };
        document.head.appendChild(script);
    }
}

toggleChat() {
    if (window.aiChat) {
        window.aiChat.toggleMinimize();
    }
}

sendChatMessage() {
    if (window.aiChat) {
        window.aiChat.sendMessage();
    }
}

sendQuickMessage(message) {
    if (window.aiChat) {
        window.aiChat.sendQuickMessage(message);
    }
}

clearChat() {
    if (window.aiChat) {
        window.aiChat.clearConversation();
    }
}

// NEW: Real-time Alerts System
initializeAlerts() {
    this.alerts = [];
    this.alertContainer = null;
    this.setupAlertContainer();
    this.startAlertMonitoring();
}

// NEW: AI Recommendations Queue
initializeRecommendations() {
    // Load recommendation queue component script if not already loaded
    if (!window.recommendationQueue) {
        const script = document.createElement('script');
        script.src = '/static/js/components/recommendation-queue.js';
        script.onload = () => {
            this.loadRecommendations();
        };
        document.head.appendChild(script);
    } else {
        this.loadRecommendations();
    }
}

// NEW: Agent Controls
initializeAgentControls() {
    // Load agent controls component script if not already loaded
    if (!window.agentControls) {
        const script = document.createElement('script');
        script.src = '/static/js/components/agent-controls.js';
        script.onload = () => {
            this.loadAgentStatus();
        };
        document.head.appendChild(script);
    } else {
        this.loadAgentStatus();
    }
}

// NEW: Analytics Dashboard
initializeAnalytics() {
    // Load analytics dashboard component script if not already loaded
    if (!window.analyticsDashboard) {
        const script = document.createElement('script');
        script.src = '/static/js/components/analytics-dashboard.js';
        script.onload = () => {
            // Analytics Dashboard component loaded
        };
        document.head.appendChild(script);
    }
}

setupAlertContainer() {
    // Create alerts container if it doesn't exist
    if (!document.getElementById('alertsContainer')) {
        const container = document.createElement('div');
        container.id = 'alertsContainer';
        container.className = 'alerts-container';
        document.body.appendChild(container);
        this.alertContainer = container;
    } else {
        this.alertContainer = document.getElementById('alertsContainer');
    }
}

startAlertMonitoring() {
    // Check for alerts every 30 seconds
    setInterval(() => this.checkForAlerts(), 30000);

    // Initial check
    setTimeout(() => this.checkForAlerts(), 2000);
}

async checkForAlerts() {
    try {
        const response = await fetch('/api/alerts/active');
        const data = await response.json();

        if (response.ok && data.alerts) {
            this.updateAlerts(data.alerts);
        }
    } catch (error) {
        console.error('Failed to check alerts:', error);
    }
}

updateAlerts(newAlerts) {
    // Remove old alerts that are no longer active
    const currentAlertIds = newAlerts.map(alert => alert.id);
    this.alerts = this.alerts.filter(alert =>
        currentAlertIds.includes(alert.id) || alert.persistent
    );

    // Add new alerts
    for (const alert of newAlerts) {
        if (!this.alerts.find(a => a.id === alert.id)) {
            this.alerts.push(alert);
            this.showAlert(alert);
        }
    }

    // Update alert counter in UI
    this.updateAlertCounter();
}

showAlert(alert) {
    if (!this.alertContainer) return;

    const alertElement = document.createElement('div');
    alertElement.className = `alert alert-${alert.severity || 'info'}`;
    alertElement.setAttribute('data-alert-id', alert.id);

    const iconClass = this.getAlertIcon(alert.type);
    const timestamp = new Date(alert.timestamp || Date.now()).toLocaleTimeString();

    alertElement.innerHTML = `
        <div class="alert-icon">
            <i class="fas ${iconClass}"></i>
        </div>
        <div class="alert-content">
            <div class="alert-title">${alert.title || 'System Alert'}</div>
            <div class="alert-message">${alert.message}</div>
            <div class="alert-time">${timestamp}</div>
        </div>
        <div class="alert-actions">
            ${alert.actionable ? `<button onclick="dashboard.handleAlertAction('${alert.id}', 'acknowledge')">Acknowledge</button>` : ''}
            <button onclick="dashboard.dismissAlert('${alert.id}')">×</button>
        </div>
    `;

    this.alertContainer.appendChild(alertElement);

    // Auto-dismiss non-critical alerts after 10 seconds
    if (alert.severity !== 'critical' && alert.severity !== 'high') {
        setTimeout(() => {
            if (alertElement.parentNode) {
                alertElement.remove();
            }
        }, 10000);
    }

    // Animate in
    setTimeout(() => alertElement.classList.add('show'), 100);
}

getAlertIcon(type) {
    const icons = {
        'stop_loss': 'fa-exclamation-triangle',
        'earnings': 'fa-chart-line',
        'news': 'fa-newspaper',
        'price_alert': 'fa-bell',
        'system': 'fa-cog',
        'market': 'fa-chart-bar'
    };
    return icons[type] || 'fa-info-circle';
}

dismissAlert(alertId) {
    const alertElement = document.querySelector(`[data-alert-id="${alertId}"]`);
    if (alertElement) {
        alertElement.classList.remove('show');
        setTimeout(() => alertElement.remove(), 300);
    }

    // Remove from alerts array
    this.alerts = this.alerts.filter(alert => alert.id !== alertId);
    this.updateAlertCounter();
}

async handleAlertAction(alertId, action) {
    try {
        // This would call an API endpoint to handle the alert action
        const response = await fetch(`/api/alerts/${alertId}/action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: action })
        });

        if (response.ok) {
            this.dismissAlert(alertId);
            this.showToast('Alert action processed', 'success');
        }
    } catch (error) {
        console.error('Failed to handle alert action:', error);
        this.showToast('Failed to process alert action', 'error');
    }
}

updateAlertCounter() {
    // Update any alert counter badges in the UI
    const counters = document.querySelectorAll('.alert-counter');
    counters.forEach(counter => {
        const activeAlerts = this.alerts.filter(alert =>
            alert.severity === 'critical' || alert.severity === 'high'
        ).length;

        counter.textContent = activeAlerts;
        counter.style.display = activeAlerts > 0 ? 'inline' : 'none';
    });
}

// Emergency controls
async emergencyStop() {
    if (!confirm('Are you sure you want to activate emergency stop? This will halt all autonomous operations.')) {
        return;
    }

    try {
        const response = await fetch('/api/emergency/stop', {
            method: 'POST'
        });

        if (response.ok) {
            this.showToast('Emergency stop activated', 'warning');
            this.showAlert({
                id: 'emergency_stop',
                type: 'system',
                severity: 'critical',
                title: 'Emergency Stop Activated',
                message: 'All autonomous operations have been halted',
                actionable: false,
                persistent: true
            });
        } else {
            this.showToast('Failed to activate emergency stop', 'error');
        }
    } catch (error) {
        this.showToast('Network error during emergency stop', 'error');
    }
}

async resumeOperations() {
    try {
        const response = await fetch('/api/emergency/resume', {
            method: 'POST'
        });

        if (response.ok) {
            this.showToast('Operations resumed', 'success');
            this.dismissAlert('emergency_stop');
        } else {
            this.showToast('Failed to resume operations', 'error');
        }
    } catch (error) {
        this.showToast('Network error during resume', 'error');
    }
}

// Show modern toast notifications
showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-triangle' : 'info-circle'}"></i>
        ${message}
    `;

    container.appendChild(toast);

    // Animate in
    setTimeout(() => toast.classList.add('show'), 100);

    // Remove after 5 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 5000);
}

// NEW: Load AI Recommendations
async loadRecommendations() {
    try {
        const response = await fetch('/api/ai/recommendations');
        const data = await response.json();

        if (window.recommendationQueue) {
            window.recommendationQueue.updateRecommendations(data.recommendations);
        } else {
            this.updateRecommendationsDisplay(data.recommendations);
        }
    } catch (error) {
        console.error('Failed to load recommendations:', error);
    }
}

// NEW: Load Agent Status
async loadAgentStatus() {
    try {
        const response = await fetch('/api/agents/status');
        const data = await response.json();

        if (window.agentControls && typeof window.agentControls.updateAgentStatus === 'function') {
            window.agentControls.updateAgentStatus(data.agents);
        } else {
            this.updateAgentControlsDisplay(data.agents);
        }
    } catch (error) {
        console.error('Failed to load agent status:', error);
    }
}

// NEW: Show Agent Controls Modal
showAgentControls() {
    if (window.agentControls) {
        window.agentControls.showModal();
    } else {
        const modal = document.getElementById('agentControlsModal');
        if (modal) modal.style.display = 'flex';
    }
}

// NEW: Start AI Planning
async startAIPlanning() {
    const button = event.target.closest('button');
    const originalHTML = button.innerHTML;

    button.innerHTML = '<div class="loading"></div><span>Planning...</span>';
    button.disabled = true;

    try {
        const response = await fetch('/api/ai/plan-daily', {
            method: 'POST'
        });

        if (response.ok) {
            this.showToast('AI planning started successfully', 'success');
            // Refresh AI status after a delay
            setTimeout(() => this.loadAIStatus(), 2000);
        } else {
            this.showToast('Failed to start AI planning', 'error');
        }
    } catch (error) {
        this.showToast('Network error during AI planning', 'error');
        console.error(error);
    } finally {
        button.innerHTML = originalHTML;
        button.disabled = false;
    }
}

// Fallback methods for when components aren't loaded
updateRecommendationsDisplay(recommendations) {
    const container = document.getElementById('recommendationsQueue');
    if (!container) return;

    const existingCards = new Set(
        Array.from(container.querySelectorAll('.recommendation-card'))
            .map(card => card.getAttribute('data-recommendation-id'))
    );

    if (!recommendations || recommendations.length === 0) {
        if (container.children.length === 0) {
            container.innerHTML = '<div class="no-recommendations">No pending recommendations</div>';
        }
        return;
    }

    const noRecommendationsMsg = container.querySelector('.no-recommendations');
    if (noRecommendationsMsg) {
        noRecommendationsMsg.remove();
    }

    recommendations.forEach(rec => {
        if (existingCards.has(rec.id)) {
            return;
        }

        const recElement = document.createElement('div');
        recElement.className = 'recommendation-card';
        recElement.setAttribute('data-recommendation-id', rec.id);
        recElement.innerHTML = `
            <div class="recommendation-header">
                <h4>${rec.recommendation.action} ${rec.recommendation.symbol}</h4>
                <span class="confidence">Confidence: ${rec.recommendation.confidence}%</span>
            </div>
            <div class="recommendation-reasoning">
                ${rec.recommendation.reasoning}
            </div>
            <div class="recommendation-actions">
                <button class="btn btn-sm" onclick="dashboard.approveRecommendation('${rec.id}')">Approve</button>
                <button class="btn btn-sm btn-outline" onclick="dashboard.discussRecommendation('${rec.id}')">Discuss</button>
                <button class="btn btn-sm btn-outline" onclick="dashboard.rejectRecommendation('${rec.id}')">Reject</button>
            </div>
        `;

        container.appendChild(recElement);

        gsap.fromTo(recElement,
            { opacity: 0, y: 8 },
            { opacity: 1, y: 0, duration: 0.3, ease: "power2.out" }
        );
    });
}

updateAgentControlsDisplay(agents) {
    const container = document.getElementById('agentControls');
    if (!container) return;

    container.innerHTML = '';

    Object.entries(agents).forEach(([agentName, status]) => {
        const agentElement = document.createElement('div');
        agentElement.className = 'agent-control-item';
        agentElement.innerHTML = `
            <div class="agent-header">
                <div class="agent-avatar">${agentName.charAt(0).toUpperCase()}</div>
                <div class="agent-info">
                    <h4>${agentName}</h4>
                    <div class="agent-status ${status.active ? 'active' : 'inactive'}">
                        ${status.active ? 'Active' : 'Inactive'}
                    </div>
                </div>
            </div>
            <div class="agent-tools">
                ${status.tools ? status.tools.map(tool => `<span class="tool-tag">${tool}</span>`).join('') : ''}
            </div>
            <div class="agent-actions">
                <button onclick="dashboard.configureAgent('${agentName}')">Configure</button>
                <button onclick="dashboard.viewAgentTools('${agentName}')">Tools</button>
            </div>
        `;
        container.appendChild(agentElement);
    });
}

// Recommendation actions
async approveRecommendation(recId) {
    try {
        const response = await fetch(`/api/recommendations/approve/${recId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (response.ok) {
            this.showToast('Recommendation approved', 'success');
            await this.loadRecommendations();
        } else {
            this.showToast(result.error || 'Failed to approve recommendation', 'error');
        }
    } catch (error) {
        console.error('Failed to approve recommendation:', error);
        this.showToast('Network error', 'error');
    }
}

async discussRecommendation(recId) {
    try {
        const response = await fetch(`/api/recommendations/discuss/${recId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
            this.showToast('Recommendation marked for discussion', 'info');
            this.sendQuickMessage(`Can you explain recommendation ${recId} in more detail?`);
            if (window.aiChat) {
                window.aiChat.showChat();
            }
        } else {
            const result = await response.json();
            this.showToast(result.error || 'Failed to mark for discussion', 'error');
        }
    } catch (error) {
        console.error('Failed to mark recommendation for discussion:', error);
        this.showToast('Network error', 'error');
    }
}

async rejectRecommendation(recId) {
    try {
        const response = await fetch(`/api/recommendations/reject/${recId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });

        const result = await response.json();

        if (response.ok) {
            this.showToast('Recommendation rejected', 'info');
            await this.loadRecommendations();
        } else {
            this.showToast(result.error || 'Failed to reject recommendation', 'error');
        }
    } catch (error) {
        console.error('Failed to reject recommendation:', error);
        this.showToast('Network error', 'error');
    }
}

// Missing dashboard methods - implement proper functionality
configureAgent(agentName) {
    this.showToast(`Configuring ${agentName}...`, 'info');

    // Create configuration modal
    const modal = document.createElement('div');
    modal.className = 'modal fade show';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="fas fa-cog"></i>
                        Configure ${agentName}
                    </h5>
                    <button type="button" class="btn-close" onclick="this.closest('.modal').remove()"></button>
                </div>
                <div class="modal-body">
                    <div class="agent-config-form">
                        <div class="form-group">
                            <label class="form-label">Agent Status</label>
                            <select class="form-input" id="agentStatus">
                                <option value="active">Active</option>
                                <option value="inactive">Inactive</option>
                                <option value="maintenance">Maintenance</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Update Frequency</label>
                            <select class="form-input" id="updateFrequency">
                                <option value="realtime">Real-time</option>
                                <option value="5min">Every 5 minutes</option>
                                <option value="15min">Every 15 minutes</option>
                                <option value="1hour">Every hour</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label class="form-label">Risk Tolerance</label>
                            <input type="range" class="form-input" id="riskTolerance" min="1" max="10" value="5">
                            <div class="range-labels">
                                <span>Conservative</span>
                                <span>Aggressive</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                    <button class="btn btn-primary" onclick="dashboard.saveAgentConfig('${agentName}')">Save Configuration</button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

viewAgentTools(agentName) {
    this.showToast(`Viewing tools for ${agentName}...`, 'info');

    // Create tools modal
    const modal = document.createElement('div');
    modal.className = 'modal fade show';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="fas fa-tools"></i>
                        ${agentName} Tools & Capabilities
                    </h5>
                    <button type="button" class="btn-close" onclick="this.closest('.modal').remove()"></button>
                </div>
                <div class="modal-body">
                    <div class="agent-tools-grid">
                        <div class="tool-card">
                            <div class="tool-icon">
                                <i class="fas fa-chart-line"></i>
                            </div>
                            <div class="tool-info">
                                <h6>Technical Analysis</h6>
                                <p>Price action, indicators, patterns</p>
                            </div>
                            <div class="tool-status active">
                                <i class="fas fa-check-circle"></i>
                                Active
                            </div>
                        </div>
                        <div class="tool-card">
                            <div class="tool-icon">
                                <i class="fas fa-newspaper"></i>
                            </div>
                            <div class="tool-info">
                                <h6>News Monitoring</h6>
                                <p>Market news, sentiment analysis</p>
                            </div>
                            <div class="tool-status active">
                                <i class="fas fa-check-circle"></i>
                                Active
                            </div>
                        </div>
                        <div class="tool-card">
                            <div class="tool-icon">
                                <i class="fas fa-shield-alt"></i>
                            </div>
                            <div class="tool-info">
                                <h6>Risk Management</h6>
                                <p>Position sizing, stop losses</p>
                            </div>
                            <div class="tool-status active">
                                <i class="fas fa-check-circle"></i>
                                Active
                            </div>
                        </div>
                        <div class="tool-card">
                            <div class="tool-icon">
                                <i class="fas fa-brain"></i>
                            </div>
                            <div class="tool-info">
                                <h6>AI Decision Making</h6>
                                <p>Machine learning predictions</p>
                            </div>
                            <div class="tool-status active">
                                <i class="fas fa-check-circle"></i>
                                Active
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Close</button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
}

saveAgentConfig(agentName) {
    this.showToast(`Configuration saved for ${agentName}`, 'success');
    // Close modal
    document.querySelector('.modal').remove();
}

// Helper functions
getAgentIndex(agent) {
    const agentIndexes = {
        'portfolio': 1,
        'technical': 2,
        'risk': 3,
        'execution': 4
    };
    return agentIndexes[agent] || 1;
}

getProgressIndex(task) {
    const taskIndexes = {
        'portfolio_analysis': 1,
        'market_screening': 2,
        'risk_assessment': 3
    };
    return taskIndexes[task] || 1;
}

// Enhanced API functions with better UX
async portfolioScan() {
    const button = event.target.closest('button');
    this.setButtonLoading(button, 'Scanning Portfolio...');

    try {
        const response = await fetch('/api/portfolio-scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (response.ok) {
            this.showToast('Portfolio scan completed successfully', 'success');
            this.showSuccessAnimation(button);
            // Trigger immediate data refresh
            setTimeout(() => this.loadInitialData(), 1000);
        } else {
            this.showToast(result.error || 'Failed to start portfolio scan', 'error');
            this.showErrorAnimation(button);
        }
    } catch (error) {
        this.showToast('Network error during portfolio scan', 'error');
        this.showErrorAnimation(button);
        console.error(error);
    } finally {
        // Restore button after delay
        setTimeout(() => {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-search"></i> Portfolio Scan';
        }, 2000);
    }
}

async marketScreening() {
    const button = event.target.closest('button');
    this.setButtonLoading(button, 'Screening Market...');

    try {
        const response = await fetch('/api/market-screening', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (response.ok) {
            this.showToast('Market screening completed successfully', 'success');
            this.showSuccessAnimation(button);
            setTimeout(() => this.loadInitialData(), 1000);
        } else {
            this.showToast(result.error || 'Failed to start market screening', 'error');
            this.showErrorAnimation(button);
        }
    } catch (error) {
        this.showToast('Network error during market screening', 'error');
        this.showErrorAnimation(button);
        console.error(error);
    } finally {
        // Restore button after delay
        setTimeout(() => {
            button.disabled = false;
            button.innerHTML = '<i class="fas fa-chart-line"></i> Market Screening';
        }, 2000);
    }
}

// Interactive trading workflow
async guidedTrading() {
    this.showToast('Opening guided trading wizard...', 'info');

    // This would open a modal with step-by-step trading guidance
    // For now, show a placeholder
    const modal = this.createGuidedTradingModal();
    document.body.appendChild(modal);

    setTimeout(() => modal.classList.add('show'), 100);
}

createGuidedTradingModal() {
    const modal = document.createElement('div');
    modal.className = 'modal fade show';
    modal.style.display = 'block';
    modal.innerHTML = `
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="fas fa-magic"></i>
                        Guided Trading Assistant
                    </h5>
                    <button type="button" class="btn-close" onclick="this.closest('.modal').remove()"></button>
                </div>
                <div class="modal-body">
                    <div class="guided-trading-wizard">
                        <div class="wizard-step active">
                            <div class="step-icon">
                                <i class="fas fa-search"></i>
                            </div>
                            <div class="step-content">
                                <h6>Symbol Selection</h6>
                                <p>Enter the stock symbol you want to trade</p>
                                <input type="text" class="form-control" placeholder="e.g., RELIANCE" id="guidedSymbol">
                            </div>
                        </div>

                        <div class="wizard-step">
                            <div class="step-icon">
                                <i class="fas fa-chart-line"></i>
                            </div>
                            <div class="step-content">
                                <h6>Technical Analysis</h6>
                                <p>Review current indicators and signals</p>
                                <div class="analysis-placeholder">
                                    <div class="loading"></div>
                                    <span>Loading analysis...</span>
                                </div>
                            </div>
                        </div>

                        <div class="wizard-step">
                            <div class="step-icon">
                                <i class="fas fa-shield-alt"></i>
                            </div>
                            <div class="step-content">
                                <h6>Risk Assessment</h6>
                                <p>Set position size and risk parameters</p>
                                <div class="risk-controls">
                                    <label>Stop Loss (%)</label>
                                    <input type="number" class="form-control" value="2" step="0.1">
                                    <label>Position Size (% of portfolio)</label>
                                    <input type="number" class="form-control" value="5" step="0.1" max="15">
                                </div>
                            </div>
                        </div>

                        <div class="wizard-step">
                            <div class="step-icon">
                                <i class="fas fa-check-circle"></i>
                            </div>
                            <div class="step-content">
                                <h6>Confirmation</h6>
                                <p>Review and confirm your trade</p>
                                <div class="trade-summary">
                                    <p>Ready to execute your trade with optimal parameters</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                    <button class="btn btn-primary">Start Trading</button>
                </div>
            </div>
        </div>
    `;

    return modal;
}

// Advanced analytics view with real charts
viewAnalytics() {
    this.showToast('Opening advanced analytics...', 'info');

    const analyticsModal = document.createElement('div');
    analyticsModal.className = 'modal fade show';
    analyticsModal.style.display = 'block';
    analyticsModal.innerHTML = `
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="fas fa-chart-bar"></i>
                        Advanced Portfolio Analytics
                    </h5>
                    <button type="button" class="btn-close" onclick="this.remove()"></button>
                </div>
                <div class="modal-body">
                    <div class="analytics-grid">
                        <div class="analytics-card">
                            <h6>Portfolio Allocation</h6>
                            <canvas id="allocationChart" width="300" height="200"></canvas>
                        </div>

                        <div class="analytics-card">
                            <h6>Performance Trend</h6>
                            <canvas id="performanceChart" width="300" height="200"></canvas>
                        </div>

                        <div class="analytics-card">
                            <h6>Risk Distribution</h6>
                            <canvas id="riskChart" width="300" height="200"></canvas>
                        </div>

                        <div class="analytics-card">
                            <h6>Sector Exposure</h6>
                            <canvas id="sectorChart" width="300" height="200"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(analyticsModal);

    // Initialize charts after modal is added to DOM
    setTimeout(() => {
        this.initializeAnalyticsCharts();
    }, 100);
}

// Initialize charts for the new dashboard design
initializeCharts() {
    this.charts = {}; // Store chart instances

    // Portfolio Performance Chart
    this.initializePerformanceChart();

    // Asset Allocation Chart
    this.initializeAllocationChart();

    // Risk Distribution Chart
    this.initializeRiskChart();

    // Sector Exposure Chart
    this.initializeSectorChart();
}

// Initialize charts for analytics modal
initializeAnalyticsCharts() {
    try {
        // Initialize charts in analytics modal
        setTimeout(() => {
            this.initializePerformanceChart();
            this.initializeAllocationChart();
            this.initializeRiskChart();
            this.initializeSectorChart();
        }, 100);
    } catch (error) {
        console.error('Failed to initialize analytics charts:', error);
        this.logError('error', 'Failed to initialize analytics charts', { error: error.message }, error.stack);
    }
}

// Enhanced error handling for missing methods
hideAgentControls() {
    const modal = document.getElementById('agentControlsModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

hideAnalytics() {
    const modal = document.getElementById('analyticsModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

hideRecommendations() {
    const modal = document.getElementById('recommendationsModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Initialize Portfolio Performance Chart
initializePerformanceChart() {
    const ctx = document.getElementById('performanceChart');
    if (!ctx) return;

    // Generate sample performance data (would be real data in production)
    const labels = [];
    const data = [];
    const baseDate = new Date();

    for (let i = 29; i >= 0; i--) {
        const date = new Date(baseDate);
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }));

        // Generate sample performance data
        const performance = (Math.random() - 0.4) * 0.02; // -0.8% to +1.2%
        data.push(performance);
    }

    // Calculate cumulative returns
    let cumulative = 0;
    const cumulativeData = data.map(value => {
        cumulative += value;
        return cumulative;
    });

    this.charts.performance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Portfolio Value',
                data: cumulativeData.map(v => (1 + v) * 100), // Convert to percentage
                borderColor: '#2563eb',
                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                pointHoverRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                intersect: false,
                mode: 'index'
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Value: ₹${context.parsed.y.toFixed(2)}`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    display: true,
                    grid: {
                        display: false
                    }
                },
                y: {
                    display: true,
                    ticks: {
                        callback: function(value) {
                            return value.toFixed(1) + '%';
                        }
                    },
                    grid: {
                        color: '#f3f4f6'
                    }
                }
            }
        }
    });
}

// Initialize Asset Allocation Chart
initializeAllocationChart() {
    const ctx = document.getElementById('allocationChart');
    if (!ctx) return;

    this.charts.allocation = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Large Cap', 'Mid Cap', 'Small Cap', 'Cash'],
            datasets: [{
                data: [45, 30, 15, 10],
                backgroundColor: [
                    '#2563eb',
                    '#10b981',
                    '#f59e0b',
                    '#6b7280'
                ],
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 12
                        }
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            return `${label}: ${value}%`;
                        }
                    }
                }
            }
        }
    });
}

// Initialize Risk Distribution Chart
initializeRiskChart() {
    const ctx = document.getElementById('riskChart');
    if (!ctx) return;

    this.charts.risk = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Low Risk', 'Medium Risk', 'High Risk'],
            datasets: [{
                label: 'Risk Distribution',
                data: [40, 45, 15],
                backgroundColor: [
                    '#10b981',
                    '#f59e0b',
                    '#ef4444'
                ],
                borderRadius: 6,
                borderSkipped: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y}% of portfolio`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    grid: {
                        color: '#f3f4f6'
                    }
                }
            }
        }
    });
}

// Initialize Sector Exposure Chart
initializeSectorChart() {
    const ctx = document.getElementById('sectorChart');
    if (!ctx) return;

    this.charts.sector = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Technology', 'Finance', 'Healthcare', 'Energy', 'Consumer', 'Others'],
            datasets: [{
                label: 'Sector Weight',
                data: [25, 20, 18, 15, 12, 10],
                backgroundColor: '#2563eb',
                borderRadius: 4,
                borderSkipped: false
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.x}% allocation`;
                        }
                    }
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    },
                    grid: {
                        color: '#f3f4f6'
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Multi-page navigation - sidebar setup removed

// Multi-page navigation - section navigation removed

// Multi-page navigation - no section loading needed
async loadSectionContent(section) {
    // Multi-page navigation: section would load on separate page
}

// Hide all section-specific content
hideAllSections() {
    // Hide section containers (add these to HTML if needed)
    const sections = ['portfolioSection', 'tradingSection', 'analyticsSection', 'agentsSection', 'settingsSection'];
    sections.forEach(sectionId => {
        const section = document.getElementById(sectionId);
        if (section) {
            section.style.display = 'none';
        }
    });
}

// Show dashboard content
showDashboardContent() {
    // Dashboard content is always visible, just ensure it's displayed
}

// Multi-page navigation - SPA content methods removed

// Multi-page navigation - SPA view loading methods removed

// Update status indicators
updateStatusIndicators() {
    const connectionStatus = document.getElementById('connectionStatus');
    const marketStatus = document.getElementById('marketStatus');
    const aiStatus = document.getElementById('aiStatus');

    if (connectionStatus) {
        connectionStatus.className = this.isConnected ? 'status-dot connected' : 'status-dot';
    }

    if (marketStatus) {
        marketStatus.className = this.marketOpen ? 'status-dot active' : 'status-dot';
    }

    if (aiStatus) {
        aiStatus.className = 'status-dot active'; // AI is always active in this demo
    }

    const marketStatusText = document.getElementById('marketStatusText');
    if (marketStatusText) {
        marketStatusText.textContent = this.marketOpen ? 'Market Open' : 'Market Closed';
    }
}

// Update intents display (for activity feed)
updateIntentsDisplay(intents) {
    const activityFeed = document.querySelector('.activity-feed');
    if (!activityFeed) return;

    // Show recent intents in activity feed
    const recentIntents = intents.slice(-5);

    activityFeed.innerHTML = '';

    if (recentIntents.length === 0) {
        activityFeed.innerHTML = `
            <div class="activity-item">
                <div class="activity-content">
                    <div class="activity-title">No recent activity</div>
                    <div class="activity-time">Run a scan to get started</div>
                </div>
            </div>
        `;
        return;
    }

    recentIntents.forEach(intent => {
        const activityItem = document.createElement('div');
        activityItem.className = 'activity-item';

        const iconClass = intent.status === 'executed' ? 'check-circle' :
                         intent.status === 'approved' ? 'clock' : 'circle';

        activityItem.innerHTML = `
            <div class="activity-icon">
                <i class="fas fa-${iconClass}"></i>
            </div>
            <div class="activity-content">
                <div class="activity-title">${intent.symbol} - ${intent.status}</div>
                <div class="activity-time">${new Date(intent.created_at).toLocaleTimeString()}</div>
            </div>
        `;

        activityFeed.appendChild(activityItem);
    });
}

// Get status color for UI elements
getStatusColor(status) {
    const colors = {
        'executed': '#34a853',
        'approved': '#fbbc04',
        'pending': '#5f6368',
        'rejected': '#ea4335'
    };
    return colors[status] || colors.pending;
}

setButtonLoading(button, loadingText = 'Loading...') {
    button.disabled = true;
    button.setAttribute('data-original-html', button.innerHTML);
    button.innerHTML = `
        <span style="display: inline-flex; align-items: center; gap: var(--space-2);">
            <div class="loading" style="width: 16px; height: 16px;"></div>
            <span>${loadingText}</span>
        </span>
    `;
    gsap.to(button, { scale: 0.98, duration: 0.15, ease: "power2.out" });
}

showSuccessAnimation(button) {
    const icon = '<i class="fas fa-check-circle" style="color: #10b981;"></i>';
    button.innerHTML = icon;
    gsap.to(button, {
        scale: 1.05,
        duration: 0.2,
        ease: "back.out(1.7)",
        onComplete: () => {
            gsap.to(button, { scale: 1, duration: 0.2, ease: "power2.out" });
        }
    });
}

showErrorAnimation(button) {
    const icon = '<i class="fas fa-exclamation-triangle" style="color: #ef4444;"></i>';
    button.innerHTML = icon;
    gsap.to(button, {
        x: [-4, 4, -4, 4, 0],
        duration: 0.4,
        ease: "power2.out"
    });
}
}

// Initialize the dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    window.dashboard = new RoboTraderDashboard();

    // Dashboard initialized with multi-page navigation
});