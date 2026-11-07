// Client-side indicator math for chart overlays. Inputs are aligned to the
// candle series; values that cannot be computed yet are null and skipped.

export function sma(values, period) {
  const out = new Array(values.length).fill(null);
  let sum = 0;
  for (let i = 0; i < values.length; i += 1) {
    const v = values[i];
    if (v == null) continue;
    sum += v;
    if (i >= period) sum -= values[i - period];
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

export function ema(values, period) {
  const out = new Array(values.length).fill(null);
  const k = 2 / (period + 1);
  let prev = null;
  for (let i = 0; i < values.length; i += 1) {
    const v = values[i];
    if (v == null) continue;
    prev = prev == null ? v : v * k + prev * (1 - k);
    if (i >= period - 1) out[i] = prev;
  }
  return out;
}

export function rsi(values, period = 14) {
  const out = new Array(values.length).fill(null);
  let gain = 0;
  let loss = 0;
  for (let i = 1; i < values.length; i += 1) {
    const diff = values[i] - values[i - 1];
    const up = Math.max(diff, 0);
    const down = Math.max(-diff, 0);
    if (i <= period) {
      gain += up;
      loss += down;
      if (i === period) {
        gain /= period;
        loss /= period;
        out[i] = loss === 0 ? 100 : 100 - 100 / (1 + gain / loss);
      }
    } else {
      gain = (gain * (period - 1) + up) / period;
      loss = (loss * (period - 1) + down) / period;
      out[i] = loss === 0 ? 100 : 100 - 100 / (1 + gain / loss);
    }
  }
  return out;
}

export function macd(values, fast = 12, slow = 26, signalPeriod = 9) {
  const fastEma = ema(values, fast);
  const slowEma = ema(values, slow);
  const line = values.map((_, i) => (fastEma[i] == null || slowEma[i] == null ? null : fastEma[i] - slowEma[i]));
  const clean = line.map((v) => (v == null ? 0 : v));
  const signal = ema(clean, signalPeriod).map((v, i) => (line[i] == null ? null : v));
  const hist = line.map((v, i) => (v == null || signal[i] == null ? null : v - signal[i]));
  return { line, signal, hist };
}

export function bollinger(values, period = 20, mult = 2) {
  const middle = sma(values, period);
  const upper = new Array(values.length).fill(null);
  const lower = new Array(values.length).fill(null);
  for (let i = period - 1; i < values.length; i += 1) {
    const window = values.slice(i - period + 1, i + 1);
    const mean = middle[i];
    const variance = window.reduce((acc, v) => acc + (v - mean) ** 2, 0) / period;
    const sd = Math.sqrt(variance);
    upper[i] = mean + mult * sd;
    lower[i] = mean - mult * sd;
  }
  return { upper, middle, lower };
}

export function toLineData(times, values) {
  const out = [];
  for (let i = 0; i < times.length; i += 1) {
    if (values[i] == null || !Number.isFinite(values[i])) continue;
    out.push({ time: times[i], value: values[i] });
  }
  return out;
}
