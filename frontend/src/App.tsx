import "./App.css"

function App() {
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

        <button type="button" className="new-chat-button">
          + Yeni sohbet
        </button>

        <nav className="sidebar-nav" aria-label="Ana menü">
          <button type="button" className="nav-item active">
            Sohbet
          </button>

          <button type="button" className="nav-item">
            Kaynaklar
          </button>

          <button type="button" className="nav-item">
            Geçmiş
          </button>
        </nav>

        <div className="sidebar-footer">
          <span className="status-dot" />
          Sistem hazır
        </div>
      </aside>

      <main className="chat-page">
        <header className="chat-header">
          <div>
            <h1>Paradoks</h1>
            <p>Telekom standartları yapay zekâ asistanı</p>
          </div>

          <button type="button" className="source-button">
            Kaynakları görüntüle
          </button>
        </header>

        <section className="welcome-section">
          <div className="welcome-icon">P</div>

          <h2>Standartlar arasında kaybolmadan sorun.</h2>

          <p>
            3GPP ve ilişkili telekom dokümanları hakkında sorularınızı
            kaynaklara dayalı olarak yanıtlayın.
          </p>

          <div className="suggestion-grid">
            <button type="button">
              5G ağ mimarisinin temel bileşenleri nelerdir?
            </button>

            <button type="button">
              Bir 3GPP teknik şartnamesini özetler misin?
            </button>

            <button type="button">
              İki farklı standart arasındaki ilişkiyi açıkla.
            </button>
          </div>
        </section>

        <form
          className="prompt-area"
          onSubmit={(event) => event.preventDefault()}
        >
          <div className="prompt-box">
            <textarea
              rows={1}
              aria-label="Mesaj"
              placeholder="Telekom standartları hakkında bir soru sorun..."
            />

            <button type="submit" className="send-button">
              Gönder
            </button>
          </div>

          <p className="prompt-note">
            Yanıtlar yüklenen ve erişilebilen kaynaklara göre oluşturulur.
          </p>
        </form>
      </main>
    </div>
  )
}

export default App