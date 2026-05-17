import { clsx } from 'clsx'
import { motion } from 'framer-motion'

interface TabsProps {
  tabs: { id: string; label: string; icon?: React.ReactNode }[]
  activeTab: string
  onChange: (id: string) => void
}

export function Tabs({ tabs, activeTab, onChange }: TabsProps) {
  return (
    <div className="flex space-x-1 bg-background rounded-lg p-1 border border-border">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={clsx(
            'relative flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-md transition-colors',
            activeTab === tab.id
              ? 'text-text'
              : 'text-textMuted hover:text-text'
          )}
        >
          {activeTab === tab.id && (
            <motion.div
              layoutId="activeTab"
              className="absolute inset-0 bg-surface rounded-md"
              transition={{ type: 'spring', duration: 0.3 }}
            />
          )}
          <span className="relative flex items-center gap-2">
            {tab.icon}
            {tab.label}
          </span>
        </button>
      ))}
    </div>
  )
}

interface TabPanelProps {
  children: React.ReactNode
  isActive: boolean
}

export function TabPanel({ children, isActive }: TabPanelProps) {
  return (
    <motion.div
      initial={false}
      animate={{
        opacity: isActive ? 1 : 0,
        display: isActive ? 'block' : 'none',
      }}
    >
      {children}
    </motion.div>
  )
}