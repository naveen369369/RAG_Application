import { createContext, useContext, useState } from 'react'

export const AppContext = createContext(null)

function getOrCreateSessionId() {
  let id = sessionStorage.getItem('rag_session_id')
  if (!id) {
    id = crypto.randomUUID()
    sessionStorage.setItem('rag_session_id', id)
  }
  return id
}

export function AppProvider({ children }) {
  const [namespace, setNamespace] = useState('all')
  const [showSources, setShowSources] = useState(true)
  const [useHyde, setUseHyde] = useState(false)
  const [useReranker, setUseReranker] = useState(false)
  const [agentMode, setAgentMode] = useState(false)
  const [sessionId] = useState(() => getOrCreateSessionId())
  const [raceDrawerOpen, setRaceDrawerOpen] = useState(false)
  const [evalDrawerOpen, setEvalDrawerOpen] = useState(false)
  const [docStudioOpen, setDocStudioOpen] = useState(false)

  return (
    <AppContext.Provider value={{
      namespace, setNamespace,
      showSources, setShowSources,
      useHyde, setUseHyde,
      useReranker, setUseReranker,
      agentMode, setAgentMode,
      sessionId,
      raceDrawerOpen, setRaceDrawerOpen,
      evalDrawerOpen, setEvalDrawerOpen,
      docStudioOpen, setDocStudioOpen,
    }}>
      {children}
    </AppContext.Provider>
  )
}

export const useAppContext = () => useContext(AppContext)

