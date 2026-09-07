import { useCallback, useState } from 'react'
import { AppProvider, useAppContext } from './context/AppContext'
import { Sidebar } from './components/Sidebar/Sidebar'
import { ChatFeed } from './components/Chat/ChatFeed'
import { useChat } from './hooks/useChat'
import { useAgent } from './hooks/useAgent'
import RaceDrawer from './components/Race/RaceDrawer'
import EvaluationDrawer from './components/Sidebar/EvaluationDrawer'
import DocumentStudioModal from './components/Sidebar/DocumentStudioModal'

const SIDEBAR_MIN = 220
const SIDEBAR_MAX = 520
const SIDEBAR_DEFAULT = 300

function RAGApp() {
  const { namespace, showSources, useHyde, useReranker, agentMode, sessionId } = useAppContext()
  const { messages: chatMessages, streaming: chatStreaming, sendMessage: sendChat, clearMessages: clearChat } = useChat()
  const { messages: agentMessages, streaming: agentStreaming, sendMessage: sendAgent, clearMessages: clearAgent } = useAgent()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [sidebarWidth, setSidebarWidth] = useState(() =>
    parseInt(localStorage.getItem('sidebar_width') || String(SIDEBAR_DEFAULT), 10)
  )
  const [resizing, setResizing] = useState(false)

  const messages = agentMode ? agentMessages : chatMessages
  const streaming = agentMode ? agentStreaming : chatStreaming

  const handleSend = useCallback((question) => {
    if (agentMode) {
      sendAgent({
        question,
        customer_id: 'C001',
        session_id: sessionId,
        temperature: 0.2,
        return_sources: showSources,
        namespace,
      })
    } else {
      sendChat({
        question,
        namespace,
        return_sources: showSources,
        use_hyde: useHyde,
        use_reranker: useReranker,
        temperature: 0.2,
      })
    }
  }, [agentMode, namespace, showSources, useHyde, useReranker, sessionId, sendAgent, sendChat])

  const handleNewChat = useCallback(() => {
    if (agentMode) clearAgent()
    else clearChat()
  }, [agentMode, clearAgent, clearChat])

  const toggleSidebar = useCallback(() => setSidebarOpen(o => !o), [])

  return (
    <div className="flex h-screen overflow-hidden bg-white">
      {/* Overlays rendered outside sidebar so they cover the full viewport */}
      <RaceDrawer />
      <EvaluationDrawer />
      <DocumentStudioModal />
      {/* Mobile overlay backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Desktop sidebar — width driven by state; transition disabled during drag */}
      <div
        className="hidden lg:flex flex-shrink-0 overflow-hidden"
        style={{
          width: sidebarOpen ? sidebarWidth : 0,
          transition: resizing ? 'none' : 'width 300ms ease-in-out',
        }}
      >
        <Sidebar
          onNewChat={handleNewChat}
          width={sidebarWidth}
          onWidthChange={(w) => {
            setSidebarWidth(w)
            localStorage.setItem('sidebar_width', String(w))
          }}
          onResizeStart={() => setResizing(true)}
          onResizeEnd={() => setResizing(false)}
          minWidth={SIDEBAR_MIN}
          maxWidth={SIDEBAR_MAX}
        />
      </div>

      {/* Mobile sidebar — fixed width slide-in overlay */}
      <div
        className={`fixed inset-y-0 left-0 z-30 lg:hidden transform transition-transform duration-300 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
        style={{ width: sidebarWidth }}
      >
        <Sidebar
          onNewChat={() => { handleNewChat(); setSidebarOpen(false) }}
          width={sidebarWidth}
          onWidthChange={() => {}}
          minWidth={SIDEBAR_MIN}
          maxWidth={SIDEBAR_MAX}
        />
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
