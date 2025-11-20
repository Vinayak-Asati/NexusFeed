const API_BASE = window.location.origin;
let selectedExchange = null;
let allSymbols = [];
let allExchanges = [];

// Theme Management
function initTheme() {
    const theme = localStorage.getItem('theme') || 'dark';
    document.body.setAttribute('data-theme', theme);
    updateThemeIcon(theme);
}

function toggleTheme() {
    const currentTheme = document.body.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const icon = document.getElementById('theme-icon');
    const text = document.getElementById('theme-text');
    if (theme === 'dark') {
        icon.textContent = '🌙';
        text.textContent = 'Dark';
    } else {
        icon.textContent = '☀️';
        text.textContent = 'Light';
    }
}

// Initialize theme on load
initTheme();

// Load configured exchanges on page load
async function loadExchanges() {
    try {
        const response = await fetch(`${API_BASE}/api/v1/exchanges/configured`);
        const data = await response.json();
        
        if (data.error) {
            return;
        }
        
        allExchanges = data.exchanges || [];
        displayExchanges(allExchanges);
    } catch (error) {
        console.error('Error loading exchanges:', error);
    }
}

function formatExchangeName(name) {
    return name
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

function displayExchanges(exchanges) {
    const dropdown = document.getElementById('exchange-dropdown');
    dropdown.innerHTML = '';
    
    if (exchanges.length === 0) {
        dropdown.innerHTML = '<div class="exchange-item"><div class="exchange-item-name">No exchanges found</div></div>';
        return;
    }
    
    exchanges.forEach(exchange => {
        const item = document.createElement('div');
        item.className = 'exchange-item';
        if (selectedExchange === exchange) {
            item.classList.add('selected');
        }
        item.innerHTML = `
            <div class="exchange-item-name">${formatExchangeName(exchange)}</div>
        `;
        item.onclick = () => {
            selectExchange(exchange);
            hideExchangeDropdown();
        };
        dropdown.appendChild(item);
    });
}

function filterExchanges() {
    const searchTerm = document.getElementById('exchange-search').value.toLowerCase().trim();
    const dropdown = document.getElementById('exchange-dropdown');
    
    if (!searchTerm) {
        displayExchanges(allExchanges);
        return;
    }
    
    const filtered = allExchanges.filter(exchange => {
        const formattedName = formatExchangeName(exchange).toLowerCase();
        return formattedName.includes(searchTerm) || exchange.toLowerCase().includes(searchTerm);
    });
    
    displayExchanges(filtered);
}

function showExchangeDropdown() {
    const dropdown = document.getElementById('exchange-dropdown');
    if (allExchanges.length > 0) {
        dropdown.style.display = 'block';
        displayExchanges(allExchanges);
    }
}

function hideExchangeDropdown() {
    const dropdown = document.getElementById('exchange-dropdown');
    dropdown.style.display = 'none';
}

// Hide dropdown when clicking outside
document.addEventListener('click', (e) => {
    const searchInput = document.getElementById('exchange-search');
    const dropdown = document.getElementById('exchange-dropdown');
    
    if (!searchInput.contains(e.target) && !dropdown.contains(e.target)) {
        hideExchangeDropdown();
    }
});

async function selectExchange(exchange) {
    selectedExchange = exchange;
    
    // Update search input with selected exchange
    document.getElementById('exchange-search').value = formatExchangeName(exchange);
    
    // Update dropdown to show selected
    displayExchanges(allExchanges);
    
    // Show symbols section
    document.getElementById('symbols-section').style.display = 'block';
    
    // Scroll to symbols section smoothly
    document.getElementById('symbols-section').scrollIntoView({ 
        behavior: 'smooth', 
        block: 'start' 
    });
    
    // Load instrument types for this exchange
    await loadInstrumentTypes(exchange);
    
    // Auto-load symbols for first instrument type
    loadSymbols();
}

async function loadInstrumentTypes(exchange) {
    try {
        const response = await fetch(`${API_BASE}/api/v1/exchanges/${exchange}/instrument-types`);
        const data = await response.json();
        
        const select = document.getElementById('instrument-type');
        select.innerHTML = '';
        
        if (data.error) {
            select.innerHTML = '<option value="spot">Spot (default)</option>';
            return;
        }
        
        if (data.instrument_types && data.instrument_types.length > 0) {
            data.instrument_types.forEach(type => {
                const option = document.createElement('option');
                option.value = type.value;
                option.textContent = type.label;
                select.appendChild(option);
            });
        } else {
            select.innerHTML = '<option value="spot">Spot</option>';
        }
    } catch (error) {
        console.error('Error loading instrument types:', error);
        const select = document.getElementById('instrument-type');
        select.innerHTML = '<option value="spot">Spot (default)</option>';
    }
}

function filterSymbols() {
    const searchTerm = document.getElementById('symbol-search').value.toLowerCase().trim();
    const container = document.getElementById('symbols-container');
    const filteredCount = document.getElementById('filtered-symbols');
    
    const hasTypeHeaders = container.querySelector('[data-type]') !== null;
    
    if (!searchTerm) {
        if (hasTypeHeaders) {
            loadAllTypes();
        } else {
            displaySymbols(allSymbols);
            if (filteredCount) {
                filteredCount.textContent = allSymbols.length;
            }
        }
        return;
    }
    
    if (hasTypeHeaders) {
        const allItems = container.querySelectorAll('.symbol-item, [data-type]');
        let visibleCount = 0;
        
        allItems.forEach(item => {
            if (item.classList.contains('symbol-item')) {
                const symbolName = (item.querySelector('.symbol-name')?.textContent || '').toLowerCase();
                const symbolDetails = (item.querySelector('.symbol-details')?.textContent || '').toLowerCase();
                
                if (symbolName.includes(searchTerm) || symbolDetails.includes(searchTerm)) {
                    item.style.display = 'flex';
                    visibleCount++;
                } else {
                    item.style.display = 'none';
                }
            } else {
                const type = item.getAttribute('data-type');
                const nextHeader = item.nextElementSibling?.getAttribute('data-type') ? 
                    item.nextElementSibling : null;
                let typeHasMatches = false;
                
                let current = item.nextElementSibling;
                while (current && current !== nextHeader && !current.hasAttribute('data-type')) {
                    if (current.classList.contains('symbol-item')) {
                        const symbolName = (current.querySelector('.symbol-name')?.textContent || '').toLowerCase();
                        const symbolDetails = (current.querySelector('.symbol-details')?.textContent || '').toLowerCase();
                        if (symbolName.includes(searchTerm) || symbolDetails.includes(searchTerm)) {
                            typeHasMatches = true;
                            break;
                        }
                    }
                    current = current.nextElementSibling;
                }
                
                item.style.display = typeHasMatches ? 'block' : 'none';
            }
        });
        
        if (filteredCount) {
            filteredCount.textContent = visibleCount;
        }
    } else {
        const filtered = allSymbols.filter(symbol => {
            const symbolName = (symbol.name || symbol.symbol || symbol).toLowerCase();
            const base = (symbol.base || '').toLowerCase();
            const quote = (symbol.quote || '').toLowerCase();
            
            return symbolName.includes(searchTerm) || 
                   base.includes(searchTerm) || 
                   quote.includes(searchTerm);
        });
        
        displaySymbols(filtered);
        if (filteredCount) {
            filteredCount.textContent = filtered.length;
        }
    }
}

function displaySymbols(symbols) {
    const container = document.getElementById('symbols-container');
    
    if (symbols.length === 0) {
        container.innerHTML = '<div class="loading">No symbols found</div>';
        return;
    }
    
    container.innerHTML = '';
    symbols.forEach(symbol => {
        const item = document.createElement('div');
        item.className = 'symbol-item';
        const symbolName = symbol.name || symbol.symbol || symbol;
        item.innerHTML = `
            <div>
                <div class="symbol-name">${symbolName}</div>
                ${symbol.base && symbol.quote ? 
                    `<div class="symbol-details">${symbol.base} / ${symbol.quote}</div>` : ''}
            </div>
        `;
        item.onclick = () => loadMarketData(selectedExchange, symbolName);
        container.appendChild(item);
    });
}

async function loadSymbols() {
    if (!selectedExchange) return;
    
    const instrumentType = document.getElementById('instrument-type').value;
    const container = document.getElementById('symbols-container');
    const errorContainer = document.getElementById('error-container');
    const stats = document.getElementById('stats');
    
    container.innerHTML = '<div class="loading">Loading symbols...</div>';
    errorContainer.innerHTML = '';
    stats.style.display = 'none';
    
    try {
        const response = await fetch(
            `${API_BASE}/api/v1/exchanges/${selectedExchange}/symbols?instrument_type=${instrumentType}`
        );
        const data = await response.json();
        
        if (data.error) {
            errorContainer.innerHTML = `<div class="error">${data.message || data.error}</div>`;
            container.innerHTML = '';
            return;
        }
        
        document.getElementById('total-symbols').textContent = data.total_symbols || 0;
        document.getElementById('instrument-type-display').textContent = data.instrument_type || instrumentType;
        stats.style.display = 'grid';
        
        allSymbols = data.symbols || [];
        document.getElementById('symbol-search').value = '';
        
        if (allSymbols.length > 0) {
            displaySymbols(allSymbols);
            document.getElementById('filtered-symbols').textContent = allSymbols.length;
        } else {
            container.innerHTML = '<div class="loading">No symbols found for this instrument type</div>';
        }
    } catch (error) {
        errorContainer.innerHTML = `<div class="error">Error loading symbols: ${error.message}</div>`;
        container.innerHTML = '';
    }
}

async function loadAllTypes() {
    if (!selectedExchange) return;
    
    const container = document.getElementById('symbols-container');
    const errorContainer = document.getElementById('error-container');
    const stats = document.getElementById('stats');
    
    container.innerHTML = '<div class="loading">Loading all symbol types...</div>';
    errorContainer.innerHTML = '';
    stats.style.display = 'none';
    
    try {
        const response = await fetch(
            `${API_BASE}/api/v1/exchanges/${selectedExchange}/symbols?all_types=true`
        );
        const data = await response.json();
        
        if (data.error) {
            errorContainer.innerHTML = `<div class="error">${data.message || data.error}</div>`;
            container.innerHTML = '';
            return;
        }
        
        document.getElementById('total-symbols').textContent = data.total_symbols || 0;
        document.getElementById('instrument-type-display').textContent = 'All Types';
        stats.style.display = 'grid';
        
        allSymbols = [];
        if (data.instrument_types) {
            Object.values(data.instrument_types).forEach(typeData => {
                if (typeData.symbols) {
                    allSymbols = allSymbols.concat(typeData.symbols);
                }
            });
        }
        
        document.getElementById('symbol-search').value = '';
        
        if (data.instrument_types) {
            container.innerHTML = '';
            Object.entries(data.instrument_types).forEach(([type, typeData]) => {
                const typeHeader = document.createElement('div');
                typeHeader.style.cssText = 'padding: 1rem; background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary)); color: white; font-weight: 600; margin-top: 1rem; border-radius: 8px; text-transform: uppercase; letter-spacing: 0.5px;';
                typeHeader.textContent = `${type} (${typeData.count} symbols)`;
                typeHeader.setAttribute('data-type', type);
                container.appendChild(typeHeader);
                
                const typeSymbols = typeData.symbols || [];
                typeSymbols.forEach(symbol => {
                    const item = document.createElement('div');
                    item.className = 'symbol-item';
                    item.setAttribute('data-type', type);
                    const symbolName = symbol.name || symbol.symbol || symbol;
                    item.innerHTML = `
                        <div>
                            <div class="symbol-name">${symbolName}</div>
                            ${symbol.base && symbol.quote ? 
                                `<div class="symbol-details">${symbol.base} / ${symbol.quote}</div>` : ''}
                        </div>
                    `;
                    item.onclick = () => loadMarketData(selectedExchange, symbolName);
                    container.appendChild(item);
                });
            });
            document.getElementById('filtered-symbols').textContent = allSymbols.length;
        } else {
            container.innerHTML = '<div class="loading">No symbols found</div>';
        }
    } catch (error) {
        errorContainer.innerHTML = `<div class="error">Error loading symbols: ${error.message}</div>`;
        container.innerHTML = '';
    }
}

async function loadMarketData(exchange, symbol) {
    const modal = document.getElementById('market-data-modal');
    const content = document.getElementById('market-data-content');
    const title = document.getElementById('modal-title');
    
    title.textContent = `${exchange.toUpperCase()} - ${symbol}`;
    content.innerHTML = '<div class="loading-spinner"></div>';
    modal.style.display = 'block';
    
    try {
        const response = await fetch(
            `${API_BASE}/api/v1/exchanges/${exchange}/market-data/${encodeURIComponent(symbol)}`
        );
        const data = await response.json();
        
        if (data.error) {
            content.innerHTML = `<div class="error">${data.message || data.error}</div>`;
            return;
        }
        
        let html = '';
        
        if (data.market_info) {
            html += `
                <div class="market-data-section">
                    <h3>Market Information</h3>
                    <div class="ticker-grid">
                        <div class="ticker-card">
                            <div class="ticker-label">Base Currency</div>
                            <div class="ticker-value">${data.market_info.base || 'N/A'}</div>
                        </div>
                        <div class="ticker-card">
                            <div class="ticker-label">Quote Currency</div>
                            <div class="ticker-value">${data.market_info.quote || 'N/A'}</div>
                        </div>
                        <div class="ticker-card">
                            <div class="ticker-label">Type</div>
                            <div class="ticker-value">${data.market_info.type || 'N/A'}</div>
                        </div>
                        <div class="ticker-card">
                            <div class="ticker-label">Status</div>
                            <div class="ticker-value">${data.market_info.active ? 'Active' : 'Inactive'}</div>
                        </div>
                    </div>
                </div>
            `;
        }
        
        if (data.ticker) {
            const ticker = data.ticker;
            const changeClass = ticker.percentage >= 0 ? 'positive' : 'negative';
            const changeSign = ticker.percentage >= 0 ? '+' : '';
            
            html += `
                <div class="market-data-section">
                    <h3>Ticker Data</h3>
                    <div class="ticker-grid">
                        <div class="ticker-card">
                            <div class="ticker-label">Last Price</div>
                            <div class="ticker-value">${formatNumber(ticker.last)}</div>
                        </div>
                        <div class="ticker-card">
                            <div class="ticker-label">Bid</div>
                            <div class="ticker-value">${formatNumber(ticker.bid)}</div>
                        </div>
                        <div class="ticker-card">
                            <div class="ticker-label">Ask</div>
                            <div class="ticker-value">${formatNumber(ticker.ask)}</div>
                        </div>
                        <div class="ticker-card">
                            <div class="ticker-label">24h High</div>
                            <div class="ticker-value">${formatNumber(ticker.high)}</div>
                        </div>
                        <div class="ticker-card">
                            <div class="ticker-label">24h Low</div>
                            <div class="ticker-value">${formatNumber(ticker.low)}</div>
                        </div>
                        <div class="ticker-card">
                            <div class="ticker-label">24h Volume</div>
                            <div class="ticker-value">${formatNumber(ticker.volume)}</div>
                        </div>
                        <div class="ticker-card">
                            <div class="ticker-label">24h Change</div>
                            <div class="ticker-value ${changeClass}">${changeSign}${formatNumber(ticker.percentage)}%</div>
                        </div>
                        <div class="ticker-card">
                            <div class="ticker-label">VWAP</div>
                            <div class="ticker-value">${formatNumber(ticker.vwap)}</div>
                        </div>
                    </div>
                </div>
            `;
        } else if (data.errors && data.errors.ticker) {
            html += `<div class="market-data-section"><div class="error">Ticker: ${data.errors.ticker}</div></div>`;
        }
        
        if (data.orderbook) {
            const ob = data.orderbook;
            let orderbookHtml = `
                <div class="market-data-section">
                    <h3>Order Book (Top 10)</h3>
                    <table class="orderbook-table">
                        <thead>
                            <tr>
                                <th>Bid Price</th>
                                <th>Bid Amount</th>
                                <th>Ask Price</th>
                                <th>Ask Amount</th>
                            </tr>
                        </thead>
                        <tbody>
            `;
            
            const maxLen = Math.max(ob.bids.length, ob.asks.length);
            for (let i = 0; i < maxLen; i++) {
                const bid = ob.bids[i] || ['-', '-'];
                const ask = ob.asks[i] || ['-', '-'];
                orderbookHtml += `
                    <tr>
                        <td class="bid-price">${bid[0] !== '-' ? formatNumber(bid[0]) : '-'}</td>
                        <td>${bid[1] !== '-' ? formatNumber(bid[1]) : '-'}</td>
                        <td class="ask-price">${ask[0] !== '-' ? formatNumber(ask[0]) : '-'}</td>
                        <td>${ask[1] !== '-' ? formatNumber(ask[1]) : '-'}</td>
                    </tr>
                `;
            }
            
            orderbookHtml += `
                        </tbody>
                    </table>
                </div>
            `;
            html += orderbookHtml;
        } else if (data.errors && data.errors.orderbook) {
            html += `<div class="market-data-section"><div class="error">Orderbook: ${data.errors.orderbook}</div></div>`;
        }
        
        if (data.trades && data.trades.length > 0) {
            html += `
                <div class="market-data-section">
                    <h3>Recent Trades</h3>
                    <div class="trades-list">
            `;
            
            data.trades.forEach(trade => {
                const sideClass = trade.side === 'buy' ? 'buy' : 'sell';
                html += `
                    <div class="trade-item ${sideClass}">
                        <div>
                            <strong>${formatNumber(trade.price)}</strong>
                            <span style="margin-left: 10px; color: var(--text-secondary);">${formatNumber(trade.amount)}</span>
                        </div>
                        <div>
                            <span style="text-transform: uppercase; font-weight: 600;">${trade.side}</span>
                            ${trade.timestamp ? `<span style="margin-left: 10px; color: var(--text-secondary); font-size: 0.9em;">${new Date(trade.timestamp).toLocaleTimeString()}</span>` : ''}
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        } else if (data.errors && data.errors.trades) {
            html += `<div class="market-data-section"><div class="error">Trades: ${data.errors.trades}</div></div>`;
        }
        
        content.innerHTML = html;
    } catch (error) {
        content.innerHTML = `<div class="error">Error loading market data: ${error.message}</div>`;
    }
}

function closeMarketDataModal() {
    document.getElementById('market-data-modal').style.display = 'none';
}

function formatNumber(num) {
    if (num === null || num === undefined || num === '-') return '-';
    const n = parseFloat(num);
    if (isNaN(n)) return '-';
    if (n >= 1000) {
        return n.toLocaleString('en-US', { maximumFractionDigits: 2 });
    }
    return n.toLocaleString('en-US', { maximumFractionDigits: 8 });
}

window.onclick = function(event) {
    const modal = document.getElementById('market-data-modal');
    if (event.target === modal) {
        closeMarketDataModal();
    }
}

// Initialize on page load
loadExchanges();

