import { Suspense, ReactNode } from 'react'

interface SafeSuspenseProps {
  children: ReactNode
  fallback?: ReactNode
}

const defaultFallback = (
  <div className="flex items-center justify-center p-8">
    <div className="flex flex-col items-center gap-3">
      <div className="w-8 h-8 border-2 border-[#238636] border-t-transparent rounded-full animate-spin" />
      <p className="text-sm text-[#8B949E]">Loading...</p>
    </div>
  </div>
)

export function SafeSuspense({ children, fallback = defaultFallback }: SafeSuspenseProps) {
  return (
    <Suspense fallback={fallback}>
      {children}
    </Suspense>
  )
}

export default SafeSuspense