import { useState } from 'react'
import Sidebar from './components/Sidebar'
import Chatbot from './components/Chatbot'
import ModelSelection from './components/ModelSelection'
import Dashboard from './components/Dashboard'

export default function App() {
  const [phase, setPhase] = useState(1)
  const [activeNav, setActiveNav] = useState('chat')
  const [profile, setProfile] = useState(null)
  const [models, setModels] = useState(null)

  const handleOnboardComplete = (data) => {
    setProfile(data)
    setPhase(2)
    setActiveNav('dashboard')
  }

  const handleModelsDeployed = (selectedModels) => {
    setModels(selectedModels)
    setPhase(3)
    setActiveNav('dashboard')
  }

  const handleNavClick = (id) => {
    if (phase === 3) setActiveNav(id)
    else if (id === 'chat' && phase >= 1) setActiveNav(id)
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-evo-bg">
      <main className="flex-1 h-full overflow-hidden">
        {phase === 1 && <Chatbot onComplete={handleOnboardComplete} />}
        {phase === 2 && <ModelSelection profile={profile} onDeploy={handleModelsDeployed} />}
        {phase === 3 && <Dashboard profile={profile} models={models} />}
      </main>
      <Sidebar active={activeNav} onNavigate={handleNavClick} phase={phase} />
    </div>
  )
}
