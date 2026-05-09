// ── EvoTrade Simulation Engine ───────────────────────────────────────────────

export const MODELS = [
  { id: 'A', name: 'Momentum-RSI Hybrid', type: 'Momentum', color: '#00FF88' },
  { id: 'B', name: 'Mean Reversion MACD', type: 'Mean Reversion', color: '#00BFFF' },
  { id: 'C', name: 'Breakout + Volume Surge', type: 'Breakout', color: '#FFD700' },
];

export function generatePriceData(n, basePrice = 142.5) {
  const data = [];
  let price = basePrice;
  const now = Date.now();
  for (let i = 0; i < n; i++) {
    const change = (Math.random() - 0.48) * 1.5;
    price = Math.max(50, price + change);
    data.push({
      time: new Date(now - (n - i) * 2000).toLocaleTimeString('en-US', { hour12: false }),
      price: parseFloat(price.toFixed(2)),
      ts: now - (n - i) * 2000,
    });
  }
  return data;
}

export function nextPrice(lastPrice) {
  const drift = 0.0001;
  const vol = 0.006;
  const change = drift + vol * (Math.random() * 2 - 1);
  return parseFloat((lastPrice * (1 + change)).toFixed(2));
}

export function generateSignals(priceData) {
  return priceData
    .filter((_, i) => i > 5 && Math.random() < 0.12)
    .map(d => ({
      ...d,
      type: Math.random() > 0.5 ? 'BUY' : 'SELL',
      model: MODELS[Math.floor(Math.random() * 3)].name,
    }));
}

export function simulateTrade(currentPrice) {
  const model = MODELS[Math.floor(Math.random() * MODELS.length)];
  const action = Math.random() > 0.5 ? 'BUY' : 'SELL';
  const size = parseFloat((Math.random() * 4 + 0.5).toFixed(2));
  const price = parseFloat((currentPrice + (Math.random() - 0.5) * 2).toFixed(2));
  return {
    id: Date.now() + Math.random(),
    timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
    model: model.name,
    modelColor: model.color,
    action,
    price,
    size,
    pnl: parseFloat(((Math.random() - 0.42) * 80).toFixed(2)),
  };
}

export function generateOrderBook(currentPrice, rows = 8) {
  const bids = [], asks = [];
  for (let i = 0; i < rows; i++) {
    const bPrice = parseFloat((currentPrice - (i + 1) * 0.18 - Math.random() * 0.12).toFixed(2));
    const aPrice = parseFloat((currentPrice + (i + 1) * 0.18 + Math.random() * 0.12).toFixed(2));
    const bSize = parseFloat((Math.random() * 12 + 1).toFixed(2));
    const aSize = parseFloat((Math.random() * 12 + 1).toFixed(2));
    bids.push({ price: bPrice, size: bSize, total: parseFloat((bSize * bPrice).toFixed(2)) });
    asks.push({ price: aPrice, size: aSize, total: parseFloat((aSize * aPrice).toFixed(2)) });
  }
  return { bids, asks };
}

export function generateSparkline(n = 30) {
  const data = [];
  let val = 100;
  for (let i = 0; i < n; i++) {
    val += (Math.random() - 0.42) * 6;
    data.push({ x: i, y: parseFloat(val.toFixed(2)) });
  }
  return data;
}

export function randomMetrics() {
  return {
    winRate: parseFloat((55 + Math.random() * 20).toFixed(1)),
    avgReturn: parseFloat((1.5 + Math.random() * 3).toFixed(2)),
    maxDrawdown: parseFloat((-5 - Math.random() * 10).toFixed(2)),
    sharpe: parseFloat((1.2 + Math.random() * 1.6).toFixed(2)),
  };
}
