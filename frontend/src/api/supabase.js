/**
 * supabase.js — Supabase JS client for direct reads + Realtime subscriptions.
 * Uses RLS-aware anon key. Auth/sessions handled via Supabase.
 */

import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = url && anonKey
  ? createClient(url, anonKey, {
      auth: { persistSession: true, autoRefreshToken: true },
      realtime: { params: { eventsPerSecond: 5 } },
    })
  : null

export const supabaseEnabled = !!supabase
