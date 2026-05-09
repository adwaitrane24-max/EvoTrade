/** sessionSlice.js — auth/user state. */

export const createSessionSlice = (set, get) => ({
  user: null,
  authChecked: false,
  setUser: (user) => set({ user, authChecked: true }),
  clearUser: () => set({ user: null }),
})
