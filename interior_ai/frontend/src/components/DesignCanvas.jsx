export default function DesignCanvas({ designData, furnitureCount, violations, onRender, loading }) {
  if (!designData) {
    return (
      <div className="panel" style={{ textAlign: 'center', padding: '60px 32px' }}>
        <div style={{ fontSize: 40, marginBottom: 16 }}>🏠</div>
        <div style={{ fontSize: 18, fontWeight: 600, marginBottom: 8 }}>No design yet</div>
        <div style={{ color: 'var(--text-secondary)' }}>Upload a floor plan and generate a design first</div>
      </div>
    );
  }

  const { room_count, furniture_count: serverCount, style } = designData;
  const fc = furnitureCount || serverCount || 0;

  return (
    <div>
      <div className="stats-bar">
        <div className="stat">
          <div className="stat-value">{room_count ?? '—'}</div>
          <div className="stat-label">Rooms</div>
        </div>
        <div className="stat">
          <div className="stat-value">{fc}</div>
          <div className="stat-label">Furniture Items</div>
        </div>
        <div className="stat">
          <div className="stat-value" style={{ textTransform: 'capitalize' }}>
            {(style || '').replace(/_/g, ' ')}
          </div>
          <div className="stat-label">Style</div>
        </div>
        <div className="stat">
          <div className="stat-value" style={{ color: violations?.length ? 'var(--danger)' : 'var(--success)' }}>
            {violations?.length ?? 0}
          </div>
          <div className="stat-label">Violations</div>
        </div>
      </div>

      {violations?.length > 0 && (
        <div className="violations">
          {violations.map((v, i) => (
            <div key={i} className="violation-item">⚠ {v}</div>
          ))}
        </div>
      )}

      <div className="panel" style={{ marginTop: 20 }}>
        <div className="panel-title">Render Your Design</div>
        <div className="panel-subtitle">Choose render quality and camera angle</div>

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, marginBottom: 20 }}>
          {[
            { mode: 'preview', label: 'Quick Preview', icon: '⚡', desc: 'Eevee, ~30s' },
            { mode: 'photoreal', label: 'Photoreal', icon: '📸', desc: 'Cycles, ~20min' },
            { mode: 'topdown', label: 'Floor Plan View', icon: '🗺', desc: 'Top-down, ~1min' },
          ].map(({ mode, label, icon, desc }) => (
            <button
              key={mode}
              className="btn btn-secondary"
              onClick={() => onRender(mode)}
              disabled={loading}
              style={{ flexDirection: 'column', alignItems: 'center', padding: '16px 24px', gap: 4 }}
            >
              <span style={{ fontSize: 24 }}>{icon}</span>
              <span style={{ fontWeight: 600 }}>{label}</span>
              <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{desc}</span>
            </button>
          ))}
        </div>

        <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
          Camera presets:
          {[
            { preset: 'eye_level', label: 'Eye Level' },
            { preset: 'three_quarter', label: '3/4 View' },
            { preset: 'top_down', label: 'Top Down' },
          ].map(({ preset, label }) => (
            <button
              key={preset}
              className="chip"
              style={{ marginLeft: 8 }}
              onClick={() => onRender('preview', preset)}
              disabled={loading}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
