/**
 * evolutionSlice.js — GA progress: per-gen fitness, top 3, AlphaGenes.
 */

export const createEvolutionSlice = (set, get) => ({
  evolutionRunning: false,
  setEvolutionRunning: (b) => set({ evolutionRunning: b }),

  generations: [],          // list of GenerationResult dicts (top_3, candidates...)
  currentGeneration: 0,
  fitnessHistory: [],
  alphaGenePerGen: [],
  finalAlphaGene: null,

  startEvolution: () =>
    set({
      evolutionRunning: true,
      generations: [],
      currentGeneration: 0,
      fitnessHistory: [],
      alphaGenePerGen: [],
      finalAlphaGene: null,
    }),

  recordGenerationStarted: (n) => set({ currentGeneration: n }),

  recordGenerationScored: ({ generation, best_fitness, avg_fitness }) =>
    set((state) => ({
      currentGeneration: generation,
      fitnessHistory: [...state.fitnessHistory, best_fitness],
    })),

  recordTop3: ({ generation, top_3 }) =>
    set((state) => {
      const existing = state.generations.find((g) => g.generation === generation)
      const next = existing
        ? state.generations.map((g) =>
            g.generation === generation ? { ...g, top_3 } : g
          )
        : [...state.generations, { generation, top_3 }]
      return { generations: next }
    }),

  recordRunCompleted: ({ final_alpha_gene, fitness_history }) =>
    set({
      evolutionRunning: false,
      finalAlphaGene: final_alpha_gene,
      fitnessHistory: fitness_history,
    }),
})
