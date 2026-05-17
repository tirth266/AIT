import { clsx } from 'clsx'
import { HTMLAttributes } from 'react'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'danger' | 'warning' | 'primary'
  size?: 'sm' | 'md'
}

export function Badge({ className, variant = 'default', size = 'md', children, ...props }: BadgeProps) {
  const baseStyles = 'inline-flex items-center font-medium rounded-md'
  const variants = {
    default: 'bg-[#21262D] text-[#8B949E]',
    success: 'bg-[#238636]/20 text-[#3FB950]',
    danger: 'bg-[#F85149]/20 text-[#F85149]',
    warning: 'bg-[#F0883E]/20 text-[#F0883E]',
    primary: 'bg-[#388BFD]/20 text-[#58A6FF]',
  }
  const sizes = {
    sm: 'px-1.5 py-0.5 text-xs',
    md: 'px-2 py-0.5 text-xs',
  }

  return (
    <span className={clsx(baseStyles, variants[variant], sizes[size], className)} {...props}>
      {children}
    </span>
  )
}

export function StatusBadge({ status }: { status: string }) {
  const config: Record<string, { variant: BadgeProps['variant']; label: string }> = {
    running: { variant: 'success', label: 'Running' },
    stopped: { variant: 'default', label: 'Stopped' },
    paused: { variant: 'warning', label: 'Paused' },
    error: { variant: 'danger', label: 'Error' },
    starting: { variant: 'primary', label: 'Starting' },
    stopping: { variant: 'warning', label: 'Stopping' },
    BUY: { variant: 'success', label: 'BUY' },
    SELL: { variant: 'danger', label: 'SELL' },
    completed: { variant: 'success', label: 'Completed' },
    pending: { variant: 'warning', label: 'Pending' },
    cancelled: { variant: 'danger', label: 'Cancelled' },
  }

  const { variant = 'default', label = status } = config[status.toLowerCase()] || {}

  return <Badge variant={variant}>{label}</Badge>
}