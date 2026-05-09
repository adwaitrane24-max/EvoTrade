import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Sidebar } from './components/layout/Sidebar'
import { ChatOnboardingPage } from './pages/ChatOnboardingPage'
import { EvolutionPage } from './pages/EvolutionPage'
import { DashboardPage } from './pages/DashboardPage'
import { useWebSocket } from './hooks/useWebSocket'

function AppInner() {
  useWebSocket('default')

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg-base">
      {/* Main content — right sidebar is fixed, so give right padding */}
      <div className="flex-1 h-full overflow-hidden relative">
        <AnimatePresence mode="wait">
          <Routes>
            <Route
              path="/"
              element={
                <motion.div
                  key="chat"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="h-full"
                >
                  <ChatOnboardingPage />
                </motion.div>
              }
            />
            <Route
              path="/evolution"
              element={
                <motion.div
                  key="evolution"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="h-full"
                >
                  <EvolutionPage />
                </motion.div>
              }
            />
            <Route
              path="/dashboard"
              element={
                <motion.div
                  key="dashboard"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="h-full"
                >
                  <DashboardPage />
                </motion.div>
              }
            />
          </Routes>
        </AnimatePresence>
      </div>

      {/* Right sidebar — fixed */}
      <Sidebar />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppInner />
    </BrowserRouter>
  )
}
