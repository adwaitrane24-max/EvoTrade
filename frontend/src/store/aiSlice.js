/**
 * aiSlice.js — AI Council reasoning cards.
 */

export const createAiSlice = (set, get) => ({
  aiCards: [],            // [{generation, reasoning, ts}]
  appendAiCard: (card) =>
    set((state) => ({
      aiCards: [{ ts: new Date().toISOString(), ...card }, ...state.aiCards].slice(0, 50),
    })),
})
