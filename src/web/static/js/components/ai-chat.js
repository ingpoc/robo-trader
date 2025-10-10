/**
 * AI Chat Interface Component
 *
 * Provides conversational trading assistance with Claude AI.
 * Handles message sending, response display, and conversation management.
 */

class AIChatInterface {
    constructor() {
        this.sessionId = null;
        this.isMinimized = false;
        this.isTyping = false;
        this.messageQueue = [];
        this.isInitialized = false;

        this.initialize();
    }

    async initialize() {
        if (this.isInitialized) return;

        this.setupDOM();
        this.setupEventListeners();
        await this.startNewSession();
        this.isInitialized = true;

        // AI Chat Interface initialized
    }

    setupDOM() {
        // Check if chat interface already exists
        if (document.getElementById('chatInterface')) {
            return;
        }

        // Load the chat HTML template
        fetch('/static/templates/components/ai_chat.html')
            .then(response => response.text())
            .then(html => {
                document.body.insertAdjacentHTML('beforeend', html);
                this.bindElements();
                this.updateChatStatus('Ready to help');
            })
            .catch(error => {
                console.error('Failed to load chat template:', error);
                // Fallback: create minimal chat interface
                this.createFallbackInterface();
            });
    }

    createFallbackInterface() {
        const chatHTML = `
            <div class="chat-interface" id="chatInterface">
                <div class="chat-header">
                    <h4>🤖 AI Assistant</h4>
                    <button onclick="dashboard.toggleChat()">×</button>
                </div>
                <div class="chat-messages" id="chatMessages"></div>
                <div class="chat-input-area">
                    <input type="text" id="chatInput" placeholder="Ask me about trading...">
                    <button onclick="dashboard.sendChatMessage()">Send</button>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', chatHTML);
        this.bindElements();
    }

    bindElements() {
        this.chatInterface = document.getElementById('chatInterface');
        this.chatMessages = document.getElementById('chatMessages');
        this.chatInput = document.getElementById('chatInput');
        this.chatSendButton = document.getElementById('chatSendButton');
        this.chatStatusDot = document.getElementById('chatStatusDot');
        this.chatStatusText = document.getElementById('chatStatusText');
        this.chatTyping = document.getElementById('chatTyping');
        this.charCount = document.getElementById('charCount');
    }

    setupEventListeners() {
        if (!this.chatInput) return;

        // Send message on Enter key
        this.chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Send message on button click
        if (this.chatSendButton) {
            this.chatSendButton.addEventListener('click', () => this.sendMessage());
        }

        // Update character count
        this.chatInput.addEventListener('input', () => {
            this.updateCharacterCount();
            this.updateSendButton();
        });

        // Handle paste events
        this.chatInput.addEventListener('paste', () => {
            setTimeout(() => this.updateCharacterCount(), 0);
        });
    }

    async startNewSession() {
        try {
            // This would create a new session via API
            // For now, we'll generate a session ID locally
            this.sessionId = `session_${Date.now()}`;
            // Started chat session
        } catch (error) {
            console.error('Failed to start chat session:', error);
        }
    }

    async sendMessage() {
        const message = this.chatInput.value.trim();
        if (!message || this.isTyping) return;

        // Add user message to UI
        this.addMessage('user', message);
        this.chatInput.value = '';

        // Update UI state
        this.setTyping(true);
        this.updateCharacterCount();

        try {
            const response = await fetch('/api/chat/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    query: message,
                    session_id: this.sessionId
                })
            });

            const data = await response.json();

            if (response.ok) {
                // Add AI response to UI
                this.addMessage('ai', data.response);

                // Handle detected intents/actions
                if (data.intents && data.intents.length > 0) {
                    this.handleDetectedIntents(data.intents);
                }

                if (data.actions && data.actions.length > 0) {
                    this.handleDetectedActions(data.actions);
                }
            } else {
                this.addMessage('ai', `Sorry, I encountered an error: ${data.detail || 'Unknown error'}`);
            }

        } catch (error) {
            console.error('Chat request failed:', error);
            this.addMessage('ai', 'Sorry, I\'m having trouble connecting right now. Please try again later.');
        } finally {
            this.setTyping(false);
        }
    }

    addMessage(sender, content, timestamp = null) {
        if (!this.chatMessages) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${sender}`;

        const timeString = timestamp ?
            new Date(timestamp).toLocaleTimeString() :
            new Date().toLocaleTimeString();

        messageDiv.innerHTML = `
            <div class="message-avatar">
                <i class="fas fa-${sender === 'user' ? 'user' : 'robot'}"></i>
            </div>
            <div class="message-content">
                <div class="message-text">${this.formatMessage(content)}</div>
                <div class="message-time">${timeString}</div>
            </div>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();

        // Remove welcome message if this is the first real message
        const welcomeMessage = this.chatMessages.querySelector('.welcome');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }

        // Hide suggestions after first message
        const suggestions = this.chatMessages.querySelector('.chat-suggestions');
        if (suggestions) {
            suggestions.style.display = 'none';
        }
    }

    formatMessage(content) {
        if (!content) return '';

        // Basic formatting - could be enhanced
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
    }

    setTyping(isTyping) {
        this.isTyping = isTyping;

        if (this.chatTyping) {
            this.chatTyping.style.display = isTyping ? 'flex' : 'none';
        }

        if (this.chatSendButton) {
            this.chatSendButton.disabled = isTyping;
        }

        this.updateSendButton();
    }

    updateCharacterCount() {
        if (!this.chatInput || !this.charCount) return;

        const count = this.chatInput.value.length;
        this.charCount.textContent = count;

        // Color coding for character limit
        if (this.charCount) {
            if (count > 450) {
                this.charCount.style.color = '#ef4444'; // red
            } else if (count > 400) {
                this.charCount.style.color = '#f59e0b'; // yellow
            } else {
                this.charCount.style.color = 'var(--color-text-muted)';
            }
        }
    }

    updateSendButton() {
        if (!this.chatSendButton || !this.chatInput) return;

        const hasText = this.chatInput.value.trim().length > 0;
        const canSend = hasText && !this.isTyping;

        this.chatSendButton.disabled = !canSend;

        if (this.chatSendButton) {
            this.chatSendButton.style.opacity = canSend ? '1' : '0.5';
        }
    }

    updateChatStatus(status, isOnline = true) {
        if (this.chatStatusText) {
            this.chatStatusText.textContent = status;
        }

        if (this.chatStatusDot) {
            this.chatStatusDot.style.background = isOnline ? '#4ade80' : '#ef4444';
        }
    }

    scrollToBottom() {
        if (this.chatMessages) {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }
    }

    handleDetectedIntents(intents) {
        // Detected intents

        // Show toast notification for detected intents
        if (window.dashboard && window.dashboard.showToast) {
            window.dashboard.showToast(`AI detected: ${intents.join(', ')}`, 'info');
        }

        // Could trigger automatic actions based on intents
        intents.forEach(intent => {
            switch (intent) {
                case 'portfolio_analysis':
                    // Could automatically trigger portfolio scan
                    break;
                case 'market_screening':
                    // Could automatically trigger market screening
                    break;
            }
        });
    }

    handleDetectedActions(actions) {
        // Detected actions

        // Handle specific actions
        actions.forEach(action => {
            switch (action) {
                case 'analyze_portfolio':
                    if (window.dashboard && window.dashboard.portfolioScan) {
                        window.dashboard.portfolioScan();
                    }
                    break;
                case 'run_market_screening':
                    if (window.dashboard && window.dashboard.marketScreening) {
                        window.dashboard.marketScreening();
                    }
                    break;
            }
        });
    }

    toggleMinimize() {
        if (!this.chatInterface) return;

        this.isMinimized = !this.isMinimized;

        if (this.isMinimized) {
            this.chatInterface.classList.add('minimized');
        } else {
            this.chatInterface.classList.remove('minimized');
        }
    }

    clearConversation() {
        if (!this.chatMessages) return;

        // Keep only the welcome message
        const welcomeMessage = `
            <div class="chat-message ai welcome">
                <div class="message-avatar">
                    <i class="fas fa-robot"></i>
                </div>
                <div class="message-content">
                    <div class="message-text">
                        Conversation cleared. How can I help you with your trading today?
                    </div>
                    <div class="message-time">Just now</div>
                </div>
            </div>
        `;

        this.chatMessages.innerHTML = welcomeMessage;
    }

    sendQuickMessage(message) {
        if (this.chatInput) {
            this.chatInput.value = message;
            this.updateCharacterCount();
            this.sendMessage();
        }
    }

    // Public API methods for dashboard integration
    show() {
        if (this.chatInterface) {
            this.chatInterface.style.display = 'flex';
            this.isMinimized = false;
            this.chatInterface.classList.remove('minimized');
        }
    }

    hide() {
        if (this.chatInterface) {
            this.chatInterface.style.display = 'none';
        }
    }

    focus() {
        if (this.chatInput) {
            this.chatInput.focus();
        }
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (!window.aiChat) {
        window.aiChat = new AIChatInterface();
    }
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AIChatInterface;
}