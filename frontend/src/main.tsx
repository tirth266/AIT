import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

if (typeof window !== 'undefined') {
  window.addEventListener('error', (event) => {
    console.error('[Global Error]', event.error)
  })

  window.addEventListener('unhandledrejection', (event) => {
    console.error('[Unhandled Promise Rejection]', event.reason)
    
    if (event.reason?.message?.includes('WebSocket')) {
      console.log('[WS] Connection issue detected')
    }
  })

  window.addEventListener('global-error', (event) => {
    console.error('[Global Custom Error]', event.detail)
  })
}

const root = document.getElementById('root')

if (!root) {
  throw new Error('Root element not found')
}

const rootElement = ReactDOM.createRoot(root)

rootElement.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)

if (import.meta.hot) {
  import.meta.hot.accept()
}