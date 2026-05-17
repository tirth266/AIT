import { create } from 'zustand'
import { settingsApi } from '../services/api'
import type { Settings, UpdateSettingsRequest } from '../types'

interface SettingsState {
  settings: Settings | null
  isLoading: boolean
  isSaving: boolean
  error: string | null
  successMessage: string | null

  fetchSettings: () => Promise<void>
  updateSettings: (data: UpdateSettingsRequest) => Promise<void>
  clearMessages: () => void
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: null,
  isLoading: false,
  isSaving: false,
  error: null,
  successMessage: null,

  fetchSettings: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await settingsApi.get()
      set({ settings: response.data.data, isLoading: false })
    } catch (error) {
      console.error('Failed to fetch settings:', error)
      set({ error: 'Failed to fetch settings', isLoading: false })
    }
  },

  updateSettings: async (data) => {
    set({ isSaving: true, error: null, successMessage: null })
    try {
      await settingsApi.update(data)
      set({ isSaving: false, successMessage: 'Settings updated successfully' })
      await settingsApi.get()
    } catch (error: unknown) {
      const err = error as { response?: { data?: { message?: string } } }
      const errorMessage = err.response?.data?.message || 'Failed to update settings'
      console.error('Failed to update settings:', error)
      set({ error: errorMessage, isSaving: false })
    }
  },

  clearMessages: () => set({ error: null, successMessage: null }),
}))

export default useSettingsStore