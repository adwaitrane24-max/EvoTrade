import { create } from 'zustand'
import { ChatMessage, UserProfile } from '../types'

interface ChatState {
  messages: ChatMessage[]
  profile: UserProfile
  profileId: string
  step: number
  isComplete: boolean
  addMessage: (msg: ChatMessage) => void
  setProfile: (p: UserProfile) => void
  setProfileId: (id: string) => void
  setStep: (s: number) => void
  setComplete: (v: boolean) => void
  reset: () => void
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  profile: {},
  profileId: '',
  step: 0,
  isComplete: false,
  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),
  setProfile: (p) => set((s) => ({ profile: { ...s.profile, ...p } })),
  setProfileId: (id) => set({ profileId: id }),
  setStep: (step) => set({ step }),
  setComplete: (isComplete) => set({ isComplete }),
  reset: () => set({ messages: [], profile: {}, profileId: '', step: 0, isComplete: false }),
}))
