import { createContext, useContext, useState } from 'react'

const AppContext = createContext(null)

export function AppProvider({ children }) {
  const [namespace, setNamespace] = useState('all')
  const [showSources, setShowSources] = useState(true)
  const [useHyde, setUseHyde] = useState(false)
  const [useReranker, setUseReranker] = useState(false)

  return (
    <AppContext.Provider value={{
      namespace, setNamespace,
      showSources, setShowSources,
      useHyde, setUseHyde,
      useReranker, setUseReranker,
    }}>
      {children}
    </AppContext.Provider>
  )
}

export const useAppContext = () => useContext(AppContext)

