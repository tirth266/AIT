import { useState, useEffect, useCallback } from 'react'
import { clsx } from 'clsx'
import { wsManager } from '../../websocket/websocket.manager'
import { Wifi, WifiOff, Loader2 } from 'lucide-react'

interface ConnectionStatusProps {
  className?: string
}

type ConnectionState = 'connected' | 'connecting' | 'disconnected' | 'reconnecting' | 'error'

export function ConnectionStatus({ className }: ConnectionStatusProps) {
  const [status, setStatus] = useState<ConnectionState>('disconnected')

  const updateStatus = useCallback(() => {
    const currentStatus = wsManager.getStatus()
    
    switch (currentStatus) {
      case 'connected':
        setStatus('connected')
        break
      case 'connecting':
      case 'reconnecting':
        setStatus('connecting')
        break
      case 'error':
        setStatus('error')
        break
      default:
        setStatus('disconnected')
    }
  }, [])

  useEffect(() => {
    updateStatus()

    const unsubConnected = wsManager.on('connected', () => {
      setStatus('connected')
    })

    const unsubDisconnected = wsManager.on('disconnected', () => {
      setStatus('disconnected')
    })

    const unsubReconnecting = wsManager.on('reconnecting', () => {
      setStatus('reconnecting')
    })

    const unsubReconnectFailed = wsManager.on('reconnect_failed', () => {
      setStatus('error')
    })

    const pollInterval = setInterval(() => {
      if (wsManager.isConnected()) {
        setStatus('connected')
      } else {
        const currentStatus = wsManager.getStatus()
        if (currentStatus === 'connecting' || currentStatus === 'reconnecting') {
          setStatus('connecting')
        } else if (currentStatus === 'error') {
          setStatus('error')
        } else {
          setStatus('disconnected')
        }
      }
    }, 2000)

    return () => {
      unsubConnected()
      unsubDisconnected()
      unsubReconnecting()
      unsubReconnectFailed()
      clearInterval(pollInterval)
    }
  }, [updateStatus])

  return (
    <div className={clsx('flex items-center gap-2 px-3 py-1.5 rounded-lg border', className, {
      'bg-green-500/10 border-green-500/20': status === 'connected',
      'bg-yellow-500/10 border-yellow-500/20': status === 'connecting' || status === 'reconnecting',
      'bg-red-500/10 border-red-500/20': status === 'disconnected' || status === 'error',
    })}>
      {status === 'connected' && (
        <>
          <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          <Wifi className="w-3.5 h-3.5 text-green-500" />
          <span className="text-xs font-medium text-green-400">Live</span>
        </>
      )}
      {(status === 'connecting' || status === 'reconnecting') && (
        <>
          <Loader2 className="w-3.5 h-3.5 text-yellow-500 animate-spin" />
          <span className="text-xs font-medium text-yellow-400">
            {status === 'reconnecting' ? 'Reconnecting...' : 'Connecting...'}
          </span>
        </>
      )}
      {(status === 'disconnected' || status === 'error') && (
        <>
          <WifiOff className="w-3.5 h-3.5 text-red-500" />
          <span className="text-xs font-medium text-red-400">
            {status === 'error' ? 'Error' : 'Offline'}
          </span>
        </>
      )}
    </div>
  )
}

export default ConnectionStatus