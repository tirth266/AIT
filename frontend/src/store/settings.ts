import { create } from 'zustand'
import { settingsApi } from '../services/api'
import type { Settings, UpdateSettingsRequest } from '../types'

export const DEFAULT_SETTINGS: Settings = {
  trading: {
    default_product: 'MIS',
    default_order_type: 'MARKET',
    default_exchange: 'NSE',
    default_validity: 'DAY',
    auto_square_off: false,
    square_off_time: '15:15',
  },
  notifications: {
    order_filled: true,
    order_cancelled: true,
    order_rejected: true,
    position_opened: true,
    position_closed: true,
    stop_loss_hit: true,
    target_hit: true,
    daily_summary: true,
    ai_signals: true,
    email_notifications: false,
    sms_notifications: false,
    push_notifications: true,
  },
  display: {
    theme: 'DARK',
    language: 'en',
    price_format: '0.00',
    show_volume: true,
    chart_type: 'candle',
  },
  api_access: {
    enabled: false,
    rate_limit: 100,
  },
  risk_management: {
    max_daily_loss: 5000,
    max_single_trade_loss: 1000,
    max_positions: 10,
    max_orders_per_minute: 20,
    position_size_percent: 5,
  },
  updated_at: new Date(0).toISOString(),
};

interface SettingsState {
  settings: Settings
  isLoading: boolean
  isSaving: boolean
  error: string | null
  successMessage: string | null

  fetchSettings: () => Promise<void>
  updateSettings: (data: UpdateSettingsRequest) => Promise<void>
  clearMessages: () => void
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: DEFAULT_SETTINGS,
  isLoading: false,
  isSaving: false,
  error: null,
  successMessage: null,

  fetchSettings: async () => {
    set({ isLoading: true, error: null })
    try {
      const response = await settingsApi.get()
      set({ settings: response.data.data || DEFAULT_SETTINGS, isLoading: false })
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
      const response = await settingsApi.get()
      if (response.data.data) {
        set({ settings: response.data.data })
      }
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