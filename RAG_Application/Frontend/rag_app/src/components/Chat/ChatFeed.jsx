import { useEffect, useRef } from 'react'
import { Menu, Sparkles, Layers, Plus } from 'lucide-react'
import { MessageBubble } from './MessageBubble'
import { WelcomeScreen } from './WelcomeScreen'
import { ChatInput } from './ChatInput'
import { useAppContext } from '../../context/AppContext'

export function ChatFeed({ messages, streaming, onSend, sidebarOpen, onToggleSidebar, onNewChat }) {
  const { namespace } = useAppContext()
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* Top header — visible on all screen sizes */}
      <header className="flex items-center gap-2 px-3 sm:px-4 h-14 bg-white border-b border-slate-200 shadow-sm flex-shrink-0">
        {/* Sidebar toggle */}
        <button
          onClick={onToggleSidebar}
          title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          className="p-2 rounded-lg hover:bg-slate-100 transition-colors flex-shrink-0 text-slate-500 hover:text-slate-700"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Brand (shown on mobile or when sidebar is collapsed on desktop) */}
        <div className={`flex items-center gap-2 ${sidebarOpen ? 'lg:hidden' : ''}`}>
          <div className="w-6 h-6 rounded-md bg-blue-600 flex items-center justify-center flex-shrink-0 text-white">
            <Sparkles className="w-3.5 h-3.5 fill-current" />
          </div>
          <span className="font-semibold text-slate-800 text-sm hidden sm:block">RAG Studio</span>
        </div>

        {/* Divider + breadcrumb (desktop) */}
        <div className={`hidden lg:flex items-center gap-2 text-sm ${sidebarOpen ? '' : 'ml-2'}`}>
          {sidebarOpen && <span className="text-slate-200">|</span>}
          <span className="text-slate-400 font-medium">Conversation</span>
          {messages.length > 0 && (
            <span className="text-slate-300 text-xs">&mdash; {messages.length} message{messages.length > 1 ? 's' : ''}</span>
          )}
        </div>

        {/* Namespace badge (desktop) */}
        {namespace && namespace !== 'all' && (
          <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] px-2 py-0.5 rounded-md bg-blue-50 border border-blue-100 text-blue-600 font-medium ml-1 flex-shrink-0">
            <Layers className="w-3 h-3" />
            {namespace}
          </span>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Streaming indicator */}
        {streaming && (
          <div className="hidden sm:flex items-center gap-1.5 text-xs text-blue-600 font-medium">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-600" />
            </span>
            Thinking…
          </div>
        )}

        {/* New chat button */}
        {messages.length > 0 && (
          <button
            onClick={onNewChat}
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-blue-600 hover:bg-slate-100 px-2.5 py-1.5 rounded-lg transition-colors flex-shrink-0"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline font-medium">New</span>
          </button>
        )}
      </header>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {messages.length === 0 ? (
          <WelcomeScreen />
        ) : (
          <div className="max-w-[760px] mx-auto px-4 sm:px-6 pt-6 pb-4">
            {messages.map((msg, i) => (
              <MessageBubble key={i} message={msg} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <ChatInput onSend={onSend} disabled={streaming} />
    </div>
  )
}
