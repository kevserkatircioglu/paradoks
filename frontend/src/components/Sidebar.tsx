export type ActiveView =
  | "chat"
  | "sources"
  | "history"

type SidebarProps = {
  activeView: ActiveView
  isLoading: boolean
  onNewChat: () => void
  onViewChange: (view: ActiveView) => void
}

function Sidebar({
  activeView,
  isLoading,
  onNewChat,
  onViewChange,
}: SidebarProps) {
  return (
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
        onClick={onNewChat}
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
          onClick={() => onViewChange("chat")}
        >
          Sohbet
        </button>

        <button
          type="button"
          className={`nav-item ${
            activeView === "sources" ? "active" : ""
          }`}
          onClick={() => onViewChange("sources")}
        >
          Kaynaklar
        </button>

        <button
          type="button"
          className={`nav-item ${
            activeView === "history" ? "active" : ""
          }`}
          onClick={() => onViewChange("history")}
        >
          Geçmiş
        </button>
      </nav>

      <div className="sidebar-footer">
        <span className="status-dot" />
        Sistem hazır
      </div>
    </aside>
  )
}

export default Sidebar