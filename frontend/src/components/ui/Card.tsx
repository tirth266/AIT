import { HTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'bordered'
  hover?: boolean
}

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, variant = 'default', hover = false, children, style, ...props }, ref) => {
    const baseStyles = 'rounded-lg p-4 transition-all duration-200'
    const variants = {
      default: 'bg-[#161B22] border border-[#21262D]',
      glass: 'bg-[#161B22]/60 backdrop-blur-lg border border-[#21262D]/50',
      bordered: 'bg-transparent border-2 border-[#21262D]',
    }

    const hoverStyles = hover ? 'hover:border-[#238636]/50 hover:shadow-sm cursor-pointer' : ''

    return (
      <div
        ref={ref}
        className={clsx(baseStyles, variants[variant], hoverStyles, className)}
        style={style}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'

export const CardHeader = ({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={clsx('mb-3 flex items-center justify-between', className)} {...props}>
    {children}
  </div>
)

export const CardTitle = ({ className, children, ...props }: HTMLAttributes<HTMLHeadingElement>) => (
  <div className={clsx('text-sm font-semibold text-[#C9D1D9]', className)} {...props}>
    {children}
  </div>
)

export const CardContent = ({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={clsx('', className)} {...props}>
    {children}
  </div>
)