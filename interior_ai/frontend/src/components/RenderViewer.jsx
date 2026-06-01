export default function RenderViewer({ renderUrl, renderJob, onReRender, loading }) {
  const status = renderJob?.status;

  return (
    <div>
      <div className="render-container">
        {renderUrl ? (
          <img
            className="render-image"
            src={renderUrl}
            alt="Interior render"
          />
        ) : (
          <div className="render-placeholder">
            {loading ? (
              <>
                <div className="render-placeholder-icon">⏳</div>
                <div>Rendering…</div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>
                  {renderJob?.mode === 'photoreal' ? 'Photoreal renders may take up to 20 minutes' : 'Preview renders take ~30 seconds'}
                </div>
              </>
            ) : (
              <>
                <div className="render-placeholder-icon">🖼</div>
                <div>No render yet</div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 8 }}>Generate a design and click Render</div>
              </>
            )}
          </div>
        )}
      </div>

      {renderJob && (
        <div style={{ padding: '12px 16px', background: 'var(--surface-elevated)', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>
          <span style={{ marginRight: 16 }}>Job: {renderJob.job_id}</span>
          <span style={{ marginRight: 16 }}>
            Status: <span style={{ color: status === 'complete' ? 'var(--success)' : status === 'failed' ? 'var(--danger)' : 'var(--accent)' }}>
              {status}
            </span>
          </span>
          {renderJob.duration_s && <span>Time: {renderJob.duration_s}s</span>}
          {renderJob.error && <div style={{ color: 'var(--danger)', marginTop: 6 }}>{renderJob.error}</div>}
        </div>
      )}

      {renderUrl && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 20 }}>
          <a
            href={renderUrl}
            download="render.png"
            className="btn btn-primary"
          >
            ↓ Download PNG
          </a>
          <button
            className="btn btn-secondary"
            onClick={() => onReRender('photoreal')}
            disabled={loading}
          >
            Re-render (Photoreal)
          </button>
        </div>
      )}

      <div className="panel">
        <div className="panel-title" style={{ fontSize: 16 }}>Render Modes</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginTop: 12 }}>
          {[
            { mode: 'preview', label: 'Quick Preview', desc: 'Eevee · ~30s · 1280×720' },
            { mode: 'photoreal', label: 'Photoreal', desc: 'Cycles · ~20min · 1920×1080' },
            { mode: 'topdown', label: 'Floor Plan View', desc: 'Top-down · 2D-style · 1920×1080' },
            { mode: 'walkthrough', label: 'Walkthrough Frame', desc: 'Wide FOV · 1920×1080' },
          ].map(({ mode, label, desc }) => (
            <button
              key={mode}
              className="btn btn-secondary"
              onClick={() => onReRender(mode)}
              disabled={loading}
            >
              <span style={{ fontWeight: 600 }}>{label}</span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{desc}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
