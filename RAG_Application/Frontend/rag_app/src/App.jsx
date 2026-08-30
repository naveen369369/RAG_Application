import { useCallback, useState } from 'react'
import { AppProvider, useAppContext } from './context/AppContext'
import { Sidebar } from './components/Sidebar/Sidebar'
import { ChatFeed } from './components/Chat/ChatFeed'
import { useChat } from './hooks/useChat'

function RAGApp() {
  const { namespace, showSources, useHyde, useReranker } = useAppContext()
  const { messages, streaming, sendMessage, clearMessages } = useChat()
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const handleSend = useCallback((question) => {
    sendMessage({
      question,
      namespace,
      return_sources: showSources,
      use_hyde: useHyde,
      use_reranker: useReranker,
      temperature: 0.2,
    })
  }, [namespace, showSources, useHyde, useReranker, sendMessage])

  const handleNewChat = useCallback(() => {
    clearMessages()
  }, [clearMessages])

  const toggleSidebar = useCallback(() => setSidebarOpen(o => !o), [])

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      {/* Mobile overlay backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Desktop sidebar — push layout (collapses to 0px, content fills space) */}
      <div
        className={`hidden lg:flex flex-shrink-0 overflow-hidden transition-all duration-300 ease-in-out ${
          sidebarOpen ? 'w-[280px]' : 'w-0'
        }`}
      >
        <Sidebar onNewChat={handleNewChat} />
      </div>

      {/* Mobile sidebar — slide-in overlay */}
      <div
        className={`fixed inset-y-0 left-0 z-30 w-[280px] lg:hidden transform transition-transform duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <Sidebar onNewChat={() => { handleNewChat(); setSidebarOpen(false) }} />
      </div>

      {/* Main area */}
      <main className="flex-1 overflow-hidden min-w-0 flex flex-col">
        <ChatFeed
          messages={messages}
          streaming={streaming}
          onSend={handleSend}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={toggleSidebar}
          onNewChat={handleNewChat}
        />
      </main>
    </div>
  )
}

export default function App() {
  return (
    <AppProvider>
      <RAGApp />
    </AppProvider>
  )
}
