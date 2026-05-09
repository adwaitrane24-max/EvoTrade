/**
 * logsSlice.js — execution + system logs (the live trade log + system feed).
 */

const MAX_FILLS = 200
const MAX_SYSTEM = 100

export const createLogsSlice = (set, get) => ({
  fills: [],
  systemLogs: [],

  appendFill: (fill) =>
    set((state) => ({ fills: [fill, ...state.fills].slice(0, MAX_FILLS) })),

  appendSystemLog: (log) =>
    set((state) => ({
      systemLogs: [{ ts: new Date().toISOString(), ...log }, ...state.systemLogs].slice(0, MAX_SYSTEM),
    })),
})
