import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react"

import AppHeader from "./components/AppHeader"
import ChatView, {
  type Message,
} from "./components/ChatView"
import HistoryView from "./components/HistoryView"
import Sidebar, {
  type ActiveView,
} from "./components/Sidebar"
import SourcesPanel from "./components/SourcesPanel"
import SourcesView from "./components/SourcesView"

import {
  sendChatMessage,
  type Source,
} from "./services/chatApi"

import "./App.css"

function App() {
  const [question, setQuestion] = useState("")
  const [messages, setMessages] = useState<Message[]>([])
  const [isLoading, setIsLoading] = useState(false)

  const [activeView, setActiveView] =
    useState<ActiveView>("chat")

  const [isSourcesPanelOpen, setIsSourcesPanelOpen] =
    useState(false)

  const mainRef = useRef<HTMLElement>(null)

  const conversationSources = useMemo(() => {
    const uniqueSources = new Map<string, Source>()

    messages.forEach((message) => {
      message.sources?.forEach((source) => {
        const sourceKey = [
          source.org,
          source.code,
          source.version,
          source.clause,
          source.source_url,
        ].join("-")

        if (!uniqueSources.has(sourceKey)) {
          uniqueSources.set(sourceKey, source)
        }
      })
    })

    return Array.from(uniqueSources.values())
  }, [messages])

  useEffect(() => {
    setIsSourcesPanelOpen(false)

    requestAnimationFrame(() => {
      window.scrollTo({
        top: 0,
        left: 0,
        behavior: "auto",
      })

      document.scrollingElement?.scrollTo({
        top: 0,
        left: 0,
        behavior: "auto",
      })

      mainRef.current?.scrollTo({
        top: 0,
        left: 0,
        behavior: "auto",
      })
    })
  }, [activeView])

  const handleSubmit = async (
    event: FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault()

    const trimmedQuestion = question.trim()

    if (!trimmedQuestion || isLoading) {
      return
    }

    const userMessage: Message = {
      id: Date.now(),
      role: "user",
      content: trimmedQuestion,
    }

    setMessages((currentMessages) => [
      ...currentMessages,
      userMessage,
    ])

    setQuestion("")
    setIsLoading(true)

    try {
      const response = await sendChatMessage(
        trimmedQuestion,
      )

      const assistantMessage: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: response.reply,
        sources: response.sources,
      }

      setMessages((currentMessages) => [
        ...currentMessages,
        assistantMessage,
      ])
    } catch (error) {
      console.error(
        "Sohbet isteği başarısız oldu:",
        error,
      )

      const errorMessage: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content:
          "Backend servisine ulaşılamadı. Lütfen FastAPI sunucusunun çalıştığını kontrol edin.",
      }

      setMessages((currentMessages) => [
        ...currentMessages,
        errorMessage,
      ])
    } finally {
      setIsLoading(false)
    }
  }

  const handleNewChat = () => {
    if (isLoading) {
      return
    }

    setMessages([])
    setQuestion("")
    setActiveView("chat")
    setIsSourcesPanelOpen(false)
  }

  return (
    <div className="app-shell">
      <Sidebar
        activeView={activeView}
        isLoading={isLoading}
        onNewChat={handleNewChat}
        onViewChange={setActiveView}
      />

      <main
        ref={mainRef}
        className="chat-page"
      >
        <AppHeader
          activeView={activeView}
          isSourcesPanelOpen={isSourcesPanelOpen}
          onOpenSourcesPanel={() =>
            setIsSourcesPanelOpen(true)
          }
        />

        {activeView === "chat" && (
          <ChatView
            question={question}
            messages={messages}
            isLoading={isLoading}
            onQuestionChange={setQuestion}
            onSubmit={handleSubmit}
          />
        )}

        {activeView === "sources" && (
          <SourcesView
            sources={conversationSources}
          />
        )}

        {activeView === "history" && (
          <HistoryView />
        )}
      </main>

      {isSourcesPanelOpen && (
        <SourcesPanel
          sources={conversationSources}
          onClose={() =>
            setIsSourcesPanelOpen(false)
          }
        />
      )}
    </div>
  )
}

export default App