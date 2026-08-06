function HistoryView() {
  return (
    <section className="workspace-view">
      <div className="workspace-view-header">
        <div>
          <span className="workspace-eyebrow">
            Konuşma kayıtları
          </span>

          <h2>Geçmiş</h2>

          <p>
            Önceki konuşmalar ve kullanılan kaynaklar
            bu bölümden tekrar açılabilecek.
          </p>
        </div>
      </div>

      <div className="workspace-empty-state">
        <div className="workspace-empty-icon">P</div>

        <h3>Henüz kayıtlı sohbet yok</h3>

        <p>
          Sohbet geçmişi özelliği etkinleştirildiğinde
          önceki konuşmalar burada tarih ve başlık
          bilgileriyle listelenecek.
        </p>
      </div>
    </section>
  )
}

export default HistoryView