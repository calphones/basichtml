import { useState, useEffect } from 'react';
import { listStyles } from '../api/client';

const STYLE_EXAMPLES = [
  "Warm modern organic living room with curved sectional, light oak finishes, black accents, soft beige palette",
  "Japandi bedroom with platform bed, white oak floors, natural linen, minimal decor",
  "Scandinavian family room — bright, airy, functional with hygge warmth",
  "Contemporary luxury open-plan with marble accents, velvet seating, dramatic lighting",
  "Mid-century modern living with teak sideboard, tapered legs, terracotta + mustard palette",
];

export default function StyleSelector({ style, prompt, onStyleChange, onPromptChange, onGenerate, loading }) {
  const [styles, setStyles] = useState([]);
  const [promptExample, setPromptExample] = useState(0);

  useEffect(() => {
    listStyles().then(setStyles).catch(() => {});
  }, []);

  const selected = styles.find(s => s.id === style);

  return (
    <div>
      <div className="panel">
        <div className="panel-title">Choose Design Style</div>
        <div className="panel-subtitle">Select the aesthetic direction for your space</div>

        <div className="style-grid">
          {styles.map(s => (
            <div
              key={s.id}
              className={`style-card ${style === s.id ? 'selected' : ''}`}
              onClick={() => onStyleChange(s.id)}
            >
              {s.palette && (
                <div className="style-swatch">
                  <div className="swatch" style={{ background: s.palette.primary }} />
                  <div className="swatch" style={{ background: s.palette.secondary }} />
                  <div className="swatch" style={{ background: s.palette.accent }} />
                  <div className="swatch" style={{ background: s.palette.neutral }} />
                </div>
              )}
              <div className="style-name">{s.id.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</div>
              <div className="style-desc">{s.description}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel" style={{ marginTop: 20 }}>
        <div className="panel-title" style={{ fontSize: 16 }}>Describe Your Vision</div>
        <div className="panel-subtitle">Natural language prompt — be as specific as you like</div>

        <div className="field">
          <label className="label">Prompt</label>
          <textarea
            className="textarea"
            rows={3}
            value={prompt}
            onChange={e => onPromptChange(e.target.value)}
            placeholder="e.g. Warm modern organic living room with curved sectional, light oak finishes..."
          />
        </div>

        <div className="suggestion-chips">
          <span style={{ fontSize: 12, color: 'var(--text-secondary)', alignSelf: 'center' }}>Examples:</span>
          {STYLE_EXAMPLES.slice(0, 3).map((ex, i) => (
            <span
              key={i}
              className="chip"
              onClick={() => onPromptChange(ex)}
            >
              {ex.slice(0, 50)}…
            </span>
          ))}
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          {selected && (
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              {selected.floor_finish} · {selected.metal_finish}
            </div>
          )}
          <button
            className="btn btn-primary"
            onClick={onGenerate}
            disabled={loading}
            style={{ fontSize: 15, padding: '12px 28px', marginLeft: 'auto' }}
          >
            {loading ? 'Generating…' : 'Generate Design →'}
          </button>
        </div>
      </div>
    </div>
  );
}
