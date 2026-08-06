import type { Source } from "../services/chatApi"
import SourceCard from "./SourceCard"

type SourcesPanelProps = {
  sources: Source[]
  onClose: () => void
}

function SourcesPanel({
  sources,
  onClose,
}: SourcesPanelProps) {
  return (
    <>
      <button
        type="button"
        className="sources-panel-backdrop"
        aria-label="Kaynak panelini kapat"
        onClick={onClose}
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
              Bu konuşmada yanıtlara dayanak olarak
              kullanılan dokümanlar.
            </p>
          </div>

          <button
            type="button"
            className="sources-panel-close"
            aria-label="Kaynak panelini kapat"
            onClick={onClose}
          >
            ×
          </button>
        </header>

        <div className="sources-panel-content">
          {sources.length === 0 ? (
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
              {sources.map((source, index) => (
                <SourceCard
                  key={`${source.code}-${source.clause}-${index}`}
                  source={source}
                />
              ))}
            </div>
          )}
        </div>
      </aside>
    </>
  )
}

export default SourcesPanel