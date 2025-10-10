/**
 * Manual Trading JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // Handle order type change
    document.getElementById('orderType').addEventListener('change', function() {
        const priceGroup = document.getElementById('priceGroup');
        const priceInput = document.getElementById('price');

        if (this.value === 'LIMIT') {
            priceGroup.style.display = 'block';
            priceInput.required = true;
        } else {
            priceGroup.style.display = 'none';
            priceInput.required = false;
            priceInput.value = '';
        }
    });

    // Handle form submission
    document.getElementById('tradeForm').addEventListener('submit', function(e) {
        e.preventDefault();
        submitTrade();
    });

    // Load trade history
    loadTradeHistory();
});

// Submit trade
async function submitTrade() {
    const formData = new FormData(document.getElementById('tradeForm'));
    const tradeData = {
        symbol: formData.get('symbol').toUpperCase(),
        side: formData.get('side'),
        quantity: parseInt(formData.get('quantity')),
        order_type: formData.get('orderType'),
        price: formData.get('price') ? parseFloat(formData.get('price')) : null
    };

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
            showSuccessModal(result.status + (result.intent_id ? `\nIntent ID: ${result.intent_id}` : ''));
            document.getElementById('tradeForm').reset();
            loadTradeHistory(); // Refresh history
        } else {
            showErrorModal(result.error || 'Trade submission failed');
        }
    } catch (error) {
        showErrorModal('Network error: ' + error.message);
    }
}

// Load trade history
async function loadTradeHistory() {
    try {
        const response = await fetch('/api/dashboard');
        const data = await response.json();

        if (data.intents && data.intents.length > 0) {
            // Filter for manual trades (those with high confidence signals)
            const manualTrades = data.intents.filter(intent =>
                intent.signal && intent.signal.confidence >= 0.9
            ).slice(-5); // Last 5 manual trades

            displayTradeHistory(manualTrades);
        }
    } catch (error) {
        console.error('Failed to load trade history:', error);
    }
}

// Display trade history
function displayTradeHistory(trades) {
    const container = document.getElementById('tradeHistory');

    if (trades.length === 0) {
        container.innerHTML = '<p class="text-muted">No recent manual trades.</p>';
        return;
    }

    let html = '<div class="list-group">';

    trades.reverse().forEach(trade => {
        const statusClass = {
            'executed': 'success',
            'approved': 'warning',
            'pending': 'secondary',
            'rejected': 'danger'
        }[trade.status] || 'secondary';

        const executionInfo = trade.execution_reports && trade.execution_reports.length > 0 ?
            `<br><small class="text-muted">Executed: ${trade.execution_reports[0].avg_price} × ${trade.execution_reports[0].fills[0].qty}</small>` : '';

        html += `
            <div class="list-group-item">
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${trade.symbol} - ${trade.signal.entry.type} ${trade.signal.side || 'BUY'}</h6>
                    <small class="badge bg-${statusClass}">${trade.status}</small>
                </div>
                <p class="mb-1">
                    Quantity: ${trade.risk_decision ? trade.risk_decision.size_qty : 'N/A'}
                    ${trade.signal.entry.price ? ` @ ₹${trade.signal.entry.price}` : ''}
                    ${executionInfo}
                </p>
                <small class="text-muted">${new Date(trade.created_at).toLocaleString()}</small>
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;
}

// Show success modal
function showSuccessModal(message) {
    document.getElementById('successMessage').textContent = message;
    new bootstrap.Modal(document.getElementById('successModal')).show();
}

// Show error modal
function showErrorModal(message) {
    document.getElementById('errorMessage').textContent = message;
    new bootstrap.Modal(document.getElementById('errorModal')).show();
}

// Input validation
function validateTradeInput() {
    const symbol = document.getElementById('symbol').value.trim();
    const quantity = document.getElementById('quantity').value;
    const side = document.getElementById('side').value;
    const orderType = document.getElementById('orderType').value;

    // Symbol validation (basic)
    if (!/^[A-Z]{2,10}$/.test(symbol)) {
        alert('Please enter a valid symbol (2-10 uppercase letters)');
        return false;
    }

    // Quantity validation
    if (quantity < 1) {
        alert('Quantity must be at least 1');
        return false;
    }

    // Required fields
    if (!side || !orderType) {
        alert('Please fill in all required fields');
        return false;
    }

    // Price validation for limit orders
    if (orderType === 'LIMIT') {
        const price = document.getElementById('price').value;
        if (!price || price <= 0) {
            alert('Please enter a valid price for limit orders');
            return false;
        }
    }

    return true;
}

// Add validation to form
document.getElementById('tradeForm').addEventListener('submit', function(e) {
    if (!validateTradeInput()) {
        e.preventDefault();
    }
});