import { useState, useEffect } from 'react';

// Material definitions matching the Python backend
const MATERIALS_BY_STYLE = {
  modern_organic: [
    { name: 'Light Oak', type: 'Wood', color: '#C8A86A', emoji: '🪵' },
    { name: 'Cream Boucle', type: 'Textile', color: '#F0EBE0', emoji: '🧶' },
    { name: 'Warm Linen', type: 'Textile', color: '#D4C4A8', emoji: '🌾' },
    { name: 'Brushed Brass', type: 'Metal', color: '#C8A04A', emoji: '✨' },
    { name: 'Warm White Paint', type: 'Paint', color: '#FAF7F2', emoji: '🎨' },
    { name: 'Natural Stone', type: 'Stone', color: '#C8B89A', emoji: '🪨' },
    { name: 'White Marble', type: 'Marble', color: '#F0EDE8', emoji: '💎' },
    { name: 'Cognac Leather', type: 'Leather', color: '#8B5E3C', emoji: '👜' },
  ],
  japandi: [
    { name: 'Natural Maple', type: 'Wood', color: '#D4B896', emoji: '🪵' },
    { name: 'Warm Linen', type: 'Textile', color: '#D4C4A8', emoji: '🌾' },
    { name: 'Slate Grey', type: 'Stone', color: '#8C8C8C', emoji: '🪨' },
    { name: 'Brushed Nickel', type: 'Metal', color: '#C0C0C0', emoji: '✨' },
    { name: 'Muted Greige', type: 'Paint', color: '#C8BFB0', emoji: '🎨' },
    { name: 'Ceramic White', type: 'Ceramic', color: '#F5F3EF', emoji: '⚪' },
  ],
  contemporary_luxury: [
    { name: 'Calacatta Gold', type: 'Marble', color: '#E8E0D4', emoji: '💎' },
    { name: 'Dark Walnut', type: 'Wood', color: '#3D2810', emoji: '🪵' },
    { name: 'Sage Velvet', type: 'Textile', color: '#7A9B7A', emoji: '🧶' },
    { name: 'Brushed Gold', type: 'Metal', color: '#D4AF37', emoji: '🥇' },
    { name: 'Onyx Matte', type: 'Paint', color: '#1A1A1A', emoji: '🎨' },
    { name: 'Cognac Leather', type: 'Leather', color: '#8B5E3C', emoji: '👜' },
  ],
};

const FALLBACK = MATERIALS_BY_STYLE.modern_organic;

export default function MaterialBoard({ style }) {
  const materials = MATERIALS_BY_STYLE[style] || FALLBACK;

  return (
    <div>
      <div className="panel">
        <div className="panel-title">Material Palette</div>
        <div className="panel-subtitle">
          Materials selected for {style?.replace(/_/g, ' ')} — all sourced from CC0 / procedural library
        </div>

        <div className="material-grid">
          {materials.map((mat, i) => (
            <div key={i} className="material-card">
              <div
                className="material-swatch"
                style={{ background: mat.color }}
              >
                <span style={{ fontSize: 28 }}>{mat.emoji}</span>
              </div>
              <div className="material-info">
                <div className="material-name">{mat.name}</div>
                <div className="material-type">{mat.type}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="panel" style={{ marginTop: 20 }}>
        <div className="panel-title" style={{ fontSize: 16 }}>Colour Palette</div>
        <div style={{ display: 'flex', gap: 16, marginTop: 12 }}>
          {materials.slice(0, 5).map((mat, i) => (
            <div key={i} style={{ textAlign: 'center' }}>
              <div style={{
                width: 60, height: 60,
                borderRadius: '50%',
                background: mat.color,
                margin: '0 auto 8px',
                border: '2px solid var(--border)',
              }} />
              <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{mat.color}</div>
              <div style={{ fontSize: 12 }}>{mat.name.split(' ')[0]}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
