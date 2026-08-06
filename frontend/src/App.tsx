import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react"

import {
  sendChatMessage,
  type Source,
} from "./services/chatApi"

import "./App.css"

type Message = {
  id: number
  role: "user" | "assistant"
  content: string
  sources?: Source[]
}

type ActiveView = "chat" | "sources" | "history"

const suggestions = [
  "5G ağ mimarisinin temel bileşenleri nelerdir?",
  "Bir 3GPP teknik şartnamesini özetler misin?",
  "İki farklı standart arasındaki ilişkiyi açıkla.",
]

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

  const pageTitle =
    activeView === "chat"
      ? "Paradoks"
      : activeView === "sources"
        ? "Kaynaklar"
        : "Geçmiş"

  const pageDescription =
    activeView === "chat"
      ? "Telekom standartları yapay zekâ asistanı"
      : activeView === "sources"
        ? "Sisteme aktarılan standart dokümanları"
        : "Önceki konuşmalar ve kaynak kayıtları"

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">P</div>

          <div className="brand-text">
            <strong>Paradoks</strong>
            <span>Standart Asistanı</span>
          </div>
        </div>

        <button
          type="button"
          className="new-chat-button"
          onClick={handleNewChat}
          disabled={isLoading}
        >
          + Yeni sohbet
        </button>

        <nav
          className="sidebar-nav"
          aria-label="Ana menü"
        >
          <button
            type="button"
            className={`nav-item ${
              activeView === "chat" ? "active" : ""
            }`}
            onClick={() => setActiveView("chat")}
          >
            Sohbet
          </button>

          <button
            type="button"
            className={`nav-item ${
              activeView === "sources" ? "active" : ""
            }`}
            onClick={() => setActiveView("sources")}
          >
            Kaynaklar
          </button>

          <button
            type="button"
            className={`nav-item ${
              activeView === "history" ? "active" : ""
            }`}
            onClick={() => setActiveView("history")}
          >
            Geçmiş
          </button>
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" />
          Sistem hazır
        </div>
      </aside>

      <main
        ref={mainRef}
        className="chat-page"
      >
        <header className="chat-header">
          <div>
            <h1>{pageTitle}</h1>
            <p>{pageDescription}</p>
          </div>

          {activeView === "chat" && (
            <button
              type="button"
              className="source-button"
              aria-controls="sources-panel"
              aria-expanded={isSourcesPanelOpen}
              onClick={() =>
                setIsSourcesPanelOpen(true)
              }
            >
              Kaynakları görüntüle
            </button>
          )}
        </header>

        {activeView === "chat" && (
          <>
            {messages.length === 0 ? (
              <section className="welcome-section">
                <div className="welcome-icon">P</div>

                <h2>
                  Standartlar arasında kaybolmadan
                  sorun.
                </h2>

                <p>
                  3GPP ve ilişkili telekom dokümanları
                  hakkında sorularınızı kaynaklara
                  dayalı olarak yanıtlayın.
                </p>

                <div className="suggestion-grid">
                  {suggestions.map((suggestion) => (
                    <button
                      key={suggestion}
                      type="button"
                      disabled={isLoading}
                      onClick={() =>
                        setQuestion(suggestion)
                      }
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </section>
            ) : (
              <section
                className="messages-section"
                aria-label="Sohbet mesajları"
              >
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`message-row ${message.role}`}
                  >
                    <div className="message-content">
                      <div className="message-bubble">
                        {message.content}
                      </div>

                      {message.role === "assistant" &&
                        message.sources &&
                        message.sources.length > 0 && (
                          <div className="message-sources">
                            <h3>Kullanılan kaynaklar</h3>

                            {message.sources.map(
                              (source, index) => (
                                <article
                                  key={`${source.code}-${source.clause}-${index}`}
                                  className="message-source-card"
                                >
                                  <div className="source-card-header">
                                    <strong>
                                      {source.org}{" "}
                                      {source.code}
                                    </strong>

                                    <span>
                                      {source.status}
                                    </span>
                                  </div>

                                  <div className="source-card-details">
                                    <span>
                                      Sürüm:{" "}
                                      {source.version}
                                    </span>

                                    <span>
                                      Madde:{" "}
                                      {source.clause}
                                    </span>

                                    <span>
                                      Uzaklık:{" "}
                                      {source.distance.toFixed(
                                        3,
                                      )}
                                    </span>
                                  </div>

                                  {source.source_url && (
                                    <a
                                      href={
                                        source.source_url
                                      }
                                      target="_blank"
                                      rel="noreferrer"
                                    >
                                      Kaynağı görüntüle
                                    </a>
                                  )}
                                </article>
                              ),
                            )}
                          </div>
                        )}
                    </div>
                  </div>
                ))}

                {isLoading && (
                  <div className="message-row assistant">
                    <div className="message-content">
                      <div className="message-bubble">
                        Yanıt hazırlanıyor...
                      </div>
                    </div>
                  </div>
                )}
              </section>
            )}

            <form
              className="prompt-area"
              onSubmit={handleSubmit}
            >
              <div className="prompt-box">
                <textarea
                  rows={1}
                  aria-label="Mesaj"
                  placeholder="Telekom standartları hakkında bir soru sorun..."
                  value={question}
                  disabled={isLoading}
                  onChange={(event) =>
                    setQuestion(event.target.value)
                  }
                  onKeyDown={(event) => {
                    if (
                      event.key === "Enter" &&
                      !event.shiftKey &&
                      !isLoading
                    ) {
                      event.preventDefault()
                      event.currentTarget.form?.requestSubmit()
                    }
                  }}
                />

                <button
                  type="submit"
                  className="send-button"
                  disabled={
                    !question.trim() || isLoading
                  }
                >
                  {isLoading ? "Bekleyin" : "Gönder"}
                </button>
              </div>

              <p className="prompt-note">
                Yanıtlar yüklenen ve erişilebilen
                kaynaklara göre oluşturulur.
              </p>
            </form>
          </>
        )}

        {activeView === "sources" && (
          <section className="workspace-view">
            <div className="workspace-view-header">
              <div>
                <span className="workspace-eyebrow">
                  Doküman yönetimi
                </span>

                <h2>Kaynaklar</h2>

                <p>
                  Sisteme aktarılan telekom
                  standartları, sürümleri ve erişim
                  durumları bu bölümde
                  görüntülenecek.
                </p>
              </div>
            </div>

            {conversationSources.length === 0 ? (
              <div className="workspace-empty-state">
                <div className="workspace-empty-icon">
                  P
                </div>

                <h3>
                  Henüz görüntülenecek kaynak yok
                </h3>

                <p>
                  Veritabanı entegrasyonu
                  tamamlandığında standart dokümanları,
                  maddeleri ve kaynak bağlantıları
                  burada listelenecek.
                </p>
              </div>
            ) : (
              <div className="workspace-source-grid">
                {conversationSources.map(
                  (source, index) => (
                    <article
                      key={`${source.code}-${source.clause}-${index}`}
                      className="message-source-card"
                    >
                      <div className="source-card-header">
                        <strong>
                          {source.org} {source.code}
                        </strong>

                        <span>{source.status}</span>
                      </div>

                      <div className="source-card-details">
                        <span>
                          Sürüm: {source.version}
                        </span>

                        <span>
                          Madde: {source.clause}
                        </span>

                        <span>
                          Uzaklık:{" "}
                          {source.distance.toFixed(3)}
                        </span>
                      </div>

                      {source.source_url && (
                        <a
                          href={source.source_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Kaynağı görüntüle
                        </a>
                      )}
                    </article>
                  ),
                )}
              </div>
            )}
          </section>
        )}

        {activeView === "history" && (
          <section className="workspace-view">
            <div className="workspace-view-header">
              <div>
                <span className="workspace-eyebrow">
                  Konuşma kayıtları
                </span>

                <h2>Geçmiş</h2>

                <p>
                  Önceki konuşmalar ve kullanılan
                  kaynaklar bu bölümden tekrar
                  açılabilecek.
                </p>
              </div>
            </div>

            <div className="workspace-empty-state">
              <div className="workspace-empty-icon">
                P
              </div>

              <h3>Henüz kayıtlı sohbet yok</h3>

              <p>
                Sohbet geçmişi özelliği
                etkinleştirildiğinde önceki
                konuşmalar burada tarih ve başlık
                bilgileriyle listelenecek.
              </p>
            </div>
          </section>
        )}
      </main>

      {isSourcesPanelOpen && (
        <>
          <button
            type="button"
            className="sources-panel-backdrop"
            aria-label="Kaynak panelini kapat"
            onClick={() =>
              setIsSourcesPanelOpen(false)
            }
          />

          <aside
            id="sources-panel"
            className="sources-panel"
            aria-label="Sohbette kullanılan kaynaklar"
          >
            <header className="sources-panel-header">
              <div>
                <h2>Sohbet kaynakları</h2>

                <p>
                  Bu konuşmada yanıtlara dayanak
                  olarak kullanılan dokümanlar.
                </p>
              </div>

              <button
                type="button"
                className="sources-panel-close"
                aria-label="Kaynak panelini kapat"
                onClick={() =>
                  setIsSourcesPanelOpen(false)
                }
              >
                ×
              </button>
            </header>

            <div className="sources-panel-content">
              {conversationSources.length === 0 ? (
                <div className="sources-empty-state">
                  <div className="sources-empty-icon">
                    P
                  </div>

                  <h3>Henüz kaynak bulunmuyor</h3>

                  <p>
                    Backend bir yanıtta kaynak
                    döndürdüğünde ilgili standartlar
                    burada listelenecek.
                  </p>
                </div>
              ) : (
                <div className="sources-panel-list">
                  {conversationSources.map(
                    (source, index) => (
                      <article
                        key={`${source.code}-${source.clause}-${index}`}
                        className="message-source-card"
                      >
                        <div className="source-card-header">
                          <strong>
                            {source.org}{" "}
                            {source.code}
                          </strong>

                          <span>{source.status}</span>
                        </div>

                        <div className="source-card-details">
                          <span>
                            Sürüm: {source.version}
                          </span>

                          <span>
                            Madde: {source.clause}
                          </span>

                          <span>
                            Uzaklık:{" "}
                            {source.distance.toFixed(3)}
                          </span>
                        </div>

                        {source.source_url && (
                          <a
                            href={source.source_url}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Kaynağı görüntüle
                          </a>
                        )}
                      </article>
                    ),
                  )}
                </div>
              )}
            </div>
          </aside>
        </>
      )}
    </div>
  )
}

export default App