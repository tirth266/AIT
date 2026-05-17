import { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { ToastContainer } from '../ui/Toast'
import { useUIStore } from '../../store'

interface AppLayoutProps {
  children: ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const { sidebarCollapsed } = useUIStore()

  return (
    <div className="min-h-screen bg-[#0D1117] text-white flex">
      <Sidebar />
      
      <motion.div
        initial={false}
        animate={{ marginLeft: sidebarCollapsed ? 72 : 240 }}
        transition={{ duration: 0.2 }}
        className="flex-1 flex flex-col min-h-screen"
      >
        <Header />
        
        <main className="flex-1 overflow-auto p-4">
          {children}
        </main>
      </motion.div>
      
      <ToastContainer />
    </div>
  )
}