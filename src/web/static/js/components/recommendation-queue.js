/**
 * Recommendation Queue Component
 *
 * Manages the display and interaction with AI-generated trading recommendations.
 * Provides approval workflow, discussion capabilities, and batch operations.
 */

class RecommendationQueue {
    constructor() {
        this.recommendations = [];
        this.selectedRecommendations = new Set();
        this.isInitialized = false;
        this.pollingInterval = null;

        this.initialize();
    }

    async initialize() {
        if (this.isInitialized) return;

        this.setupDOM();
        this.setupEventListeners();
        await this.loadRecommendations();
        this.startPolling();
        this.isInitialized = true;

        // Recommendation Queue initialized
    }

    setupDOM() {
        // Check if recommendation queue already exists
        if (document.getElementById('recommendationsQueue')) {
            return;
        }

        // Load the recommendations HTML template
        fetch('/static/templates/components/recommendations.html')
            .then(response => response.text())
            .then(html => {
                document.body.insertAdjacentHTML('beforeend', html);
                this.bindElements();
            })
            .catch(error => {
                console.error('Failed to load recommendations template:', error);
                this.createFallbackInterface();
            });
    }

    createFallbackInterface() {
        const html = `
            <div class="recommendations-modal" id="recommendationsModal" style="display: none;">
                <div class="modal-backdrop" onclick="dashboard.hideRecommendations()"></div>
                <div class="modal-content">
                    <div class="modal-header">
                        <h3>🤖 AI Recommendations</h3>
                        <button onclick="dashboard.hideRecommendations()">×</button>
                    </div>
                    <div class="modal-body">
                        <div id="recommendationsQueue" class="recommendations-queue">
                            <div class="no-recommendations">No pending recommendations</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', html);
        this.bindElements();
    }

    bindElements() {
        this.modal = document.getElementById('recommendationsModal');
        this.queue = document.getElementById('recommendationsQueue');
        this.selectAllCheckbox = document.getElementById('selectAllRecommendations');
        this.batchApproveBtn = document.getElementById('batchApproveBtn');
        this.batchRejectBtn = document.getElementById('batchRejectBtn');
        this.filterButtons = document.querySelectorAll('.filter-btn');
    }

    setupEventListeners() {
        if (!this.queue) return;

        // Select all checkbox
        if (this.selectAllCheckbox) {
            this.selectAllCheckbox.addEventListener('change', (e) => {
                this.toggleSelectAll(e.target.checked);
            });
        }

        // Batch action buttons
        if (this.batchApproveBtn) {
            this.batchApproveBtn.addEventListener('click', () => this.batchApprove());
        }

        if (this.batchRejectBtn) {
            this.batchRejectBtn.addEventListener('click', () => this.batchReject());
        }

        // Filter buttons
        if (this.filterButtons) {
            this.filterButtons.forEach(btn => {
                btn.addEventListener('click', (e) => {
                    const filter = e.target.dataset.filter;
                    this.filterRecommendations(filter);
                    this.updateFilterButtons(e.target);
                });
            });
        }
    }

    async loadRecommendations() {
        try {
            const response = await fetch('/api/ai/recommendations');
            const data = await response.json();

            if (response.ok) {
                this.recommendations = data.recommendations || [];
                this.updateDisplay();
                this.updateCounter();
            } else {
                console.error('Failed to load recommendations:', data);
                this.showError('Failed to load recommendations');
            }
        } catch (error) {
            console.error('Error loading recommendations:', error);
            this.showError('Network error loading recommendations');
        }
    }

    updateDisplay() {
        if (!this.queue) return;

        if (this.recommendations.length === 0) {
            this.queue.innerHTML = '<div class="no-recommendations">No pending recommendations</div>';
            return;
        }

        this.queue.innerHTML = '';

        this.recommendations.forEach(rec => {
            const recElement = this.createRecommendationElement(rec);
            this.queue.appendChild(recElement);
        });

        this.updateBatchButtons();
    }

    createRecommendationElement(recommendation) {
        const element = document.createElement('div');
        element.className = 'recommendation-card';
        element.dataset.id = recommendation.id;

        const confidence = recommendation.recommendation?.confidence || 0;
        const confidenceClass = confidence >= 0.8 ? 'high' : confidence >= 0.6 ? 'medium' : 'low';
        const confidenceText = `${(confidence * 100).toFixed(0)}%`;

        const action = recommendation.recommendation?.action || 'UNKNOWN';
        const symbol = recommendation.recommendation?.symbol || 'N/A';
        const reasoning = recommendation.recommendation?.reasoning || 'No reasoning provided';

        element.innerHTML = `
            <div class="recommendation-header">
                <div class="recommendation-checkbox">
                    <input type="checkbox" class="rec-checkbox" data-id="${recommendation.id}">
                </div>
                <div class="recommendation-title">
                    <h4>${action} ${symbol}</h4>
                    <span class="confidence-badge ${confidenceClass}">${confidenceText}</span>
                </div>
                <div class="recommendation-time">
                    ${this.formatTime(recommendation.created_at)}
                </div>
            </div>

            <div class="recommendation-content">
                <div class="recommendation-reasoning">
                    ${reasoning}
                </div>

                ${this.renderRecommendationDetails(recommendation.recommendation)}
            </div>

            <div class="recommendation-actions">
                <button class="btn btn-success btn-sm" onclick="dashboard.approveRecommendation('${recommendation.id}')">
                    <i class="fas fa-check"></i> Approve
                </button>
                <button class="btn btn-warning btn-sm" onclick="dashboard.discussRecommendation('${recommendation.id}')">
                    <i class="fas fa-comments"></i> Discuss
                </button>
                <button class="btn btn-danger btn-sm" onclick="dashboard.rejectRecommendation('${recommendation.id}')">
                    <i class="fas fa-times"></i> Reject
                </button>
            </div>
        `;

        // Add checkbox event listener
        const checkbox = element.querySelector('.rec-checkbox');
        if (checkbox) {
            checkbox.addEventListener('change', (e) => {
                this.toggleRecommendationSelection(recommendation.id, e.target.checked);
            });
        }

        return element;
    }

    renderRecommendationDetails(rec) {
        if (!rec) return '';

        let details = '<div class="recommendation-details">';

        // Entry/exit details
        if (rec.entry_price || rec.quantity) {
            details += '<div class="detail-row">';
            if (rec.entry_price) {
                details += `<span><strong>Price:</strong> ₹${rec.entry_price.toFixed(2)}</span>`;
            }
            if (rec.quantity) {
                details += `<span><strong>Quantity:</strong> ${rec.quantity}</span>`;
            }
            details += '</div>';
        }

        // Stop loss and target
        if (rec.stop_loss || rec.target_price) {
            details += '<div class="detail-row">';
            if (rec.stop_loss) {
                details += `<span><strong>Stop Loss:</strong> ₹${rec.stop_loss.toFixed(2)}</span>`;
            }
            if (rec.target_price) {
                details += `<span><strong>Target:</strong> ₹${rec.target_price.toFixed(2)}</span>`;
            }
            details += '</div>';
        }

        // Risk metrics
        if (rec.risk_pct || rec.position_size_pct) {
            details += '<div class="detail-row">';
            if (rec.risk_pct) {
                details += `<span><strong>Risk:</strong> ${(rec.risk_pct * 100).toFixed(1)}%</span>`;
            }
            if (rec.position_size_pct) {
                details += `<span><strong>Position Size:</strong> ${(rec.position_size_pct * 100).toFixed(1)}%</span>`;
            }
            details += '</div>';
        }

        details += '</div>';
        return details;
    }

    formatTime(timestamp) {
        if (!timestamp) return 'Just now';

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

    toggleRecommendationSelection(recId, selected) {
        if (selected) {
            this.selectedRecommendations.add(recId);
        } else {
            this.selectedRecommendations.delete(recId);
        }

        this.updateBatchButtons();
        this.updateSelectAllCheckbox();
    }

    toggleSelectAll(selected) {
        const checkboxes = this.queue.querySelectorAll('.rec-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.checked = selected;
            this.toggleRecommendationSelection(checkbox.dataset.id, selected);
        });
    }

    updateSelectAllCheckbox() {
        if (!this.selectAllCheckbox) return;

        const totalCheckboxes = this.queue.querySelectorAll('.rec-checkbox').length;
        const checkedCheckboxes = this.queue.querySelectorAll('.rec-checkbox:checked').length;

        this.selectAllCheckbox.checked = totalCheckboxes > 0 && checkedCheckboxes === totalCheckboxes;
        this.selectAllCheckbox.indeterminate = checkedCheckboxes > 0 && checkedCheckboxes < totalCheckboxes;
    }

    updateBatchButtons() {
        if (!this.batchApproveBtn || !this.batchRejectBtn) return;

        const hasSelection = this.selectedRecommendations.size > 0;

        this.batchApproveBtn.disabled = !hasSelection;
        this.batchRejectBtn.disabled = !hasSelection;

        this.batchApproveBtn.textContent = hasSelection ?
            `Approve Selected (${this.selectedRecommendations.size})` :
            'Approve Selected';

        this.batchRejectBtn.textContent = hasSelection ?
            `Reject Selected (${this.selectedRecommendations.size})` :
            'Reject Selected';
    }

    async batchApprove() {
        if (this.selectedRecommendations.size === 0) return;

        const confirmed = confirm(`Approve ${this.selectedRecommendations.size} recommendation(s)?`);
        if (!confirmed) return;

        let successCount = 0;
        let errorCount = 0;

        for (const recId of this.selectedRecommendations) {
            try {
                await this.approveRecommendation(recId);
                successCount++;
            } catch (error) {
                console.error(`Failed to approve ${recId}:`, error);
                errorCount++;
            }
        }

        // Show results
        if (window.dashboard && window.dashboard.showToast) {
            if (errorCount === 0) {
                window.dashboard.showToast(`Successfully approved ${successCount} recommendation(s)`, 'success');
            } else {
                window.dashboard.showToast(`Approved ${successCount}, failed ${errorCount}`, 'warning');
            }
        }

        // Clear selection and reload
        this.selectedRecommendations.clear();
        await this.loadRecommendations();
    }

    async batchReject() {
        if (this.selectedRecommendations.size === 0) return;

        const reason = prompt('Reason for rejection (optional):') || 'Batch rejection';

        let successCount = 0;
        let errorCount = 0;

        for (const recId of this.selectedRecommendations) {
            try {
                await this.rejectRecommendation(recId, reason);
                successCount++;
            } catch (error) {
                console.error(`Failed to reject ${recId}:`, error);
                errorCount++;
            }
        }

        // Show results
        if (window.dashboard && window.dashboard.showToast) {
            if (errorCount === 0) {
                window.dashboard.showToast(`Successfully rejected ${successCount} recommendation(s)`, 'info');
            } else {
                window.dashboard.showToast(`Rejected ${successCount}, failed ${errorCount}`, 'warning');
            }
        }

        // Clear selection and reload
        this.selectedRecommendations.clear();
        await this.loadRecommendations();
    }

    async approveRecommendation(recId) {
        try {
            const response = await fetch('/api/chat/approve-recommendation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recommendation_id: recId,
                    action: 'approve'
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Failed to approve recommendation ${recId}:`, error);
            throw error;
        }
    }

    async rejectRecommendation(recId, reason = 'Rejected by user') {
        try {
            const response = await fetch('/api/chat/approve-recommendation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    recommendation_id: recId,
                    action: 'reject',
                    modifications: { reason: reason }
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`Failed to reject recommendation ${recId}:`, error);
            throw error;
        }
    }

    filterRecommendations(filter) {
        const cards = this.queue.querySelectorAll('.recommendation-card');

        cards.forEach(card => {
            const confidence = parseFloat(card.querySelector('.confidence-badge').textContent) / 100;
            let show = true;

            switch (filter) {
                case 'high':
                    show = confidence >= 0.8;
                    break;
                case 'medium':
                    show = confidence >= 0.6 && confidence < 0.8;
                    break;
                case 'low':
                    show = confidence < 0.6;
                    break;
                default:
                    show = true;
            }

            card.style.display = show ? 'block' : 'none';
        });
    }

    updateFilterButtons(activeButton) {
        this.filterButtons.forEach(btn => {
            btn.classList.remove('active');
        });
        activeButton.classList.add('active');
    }

    updateCounter() {
        // Update any recommendation counters in the UI
        const counters = document.querySelectorAll('.recommendation-counter');
        counters.forEach(counter => {
            const count = this.recommendations.length;
            counter.textContent = count;
            counter.style.display = count > 0 ? 'inline' : 'none';
        });
    }

    showError(message) {
        if (!this.queue) return;

        this.queue.innerHTML = `
            <div class="error-message">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${message}</p>
                <button onclick="this.loadRecommendations()">Retry</button>
            </div>
        `;
    }

    startPolling() {
        // Poll for new recommendations every 30 seconds
        this.pollingInterval = setInterval(() => {
            this.loadRecommendations();
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

    refresh() {
        this.loadRecommendations();
    }

    destroy() {
        this.stopPolling();
        if (this.modal) {
            this.modal.remove();
        }
    }
}

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (!window.recommendationQueue) {
        window.recommendationQueue = new RecommendationQueue();
    }
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RecommendationQueue;
}