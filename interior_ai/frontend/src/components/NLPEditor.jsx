import { useState } from 'react';

const COMMAND_SUGGESTIONS = [
  "Move sofa closer to the fireplace",
  "Make the room brighter",
  "Use lighter wood flooring",
  "Replace sectional with a curved one",
  "Add more storage",
  "Use warmer lighting",
  "Make it more japandi style",
  "Add a reading nook",
  "Remove the accent chair",
  "Use cognac leather on the sofa",
];

export default function NLPEditor({ sessionId, furnitureCount, onCommand, onUndo, onRender, loading }) {
  const [input, setInput] = useState('');
  const [history, setHistory] = useState([]);
  const [lastResult, setLastResult] = useState(null);

  const handleSubmit = async (cmd) => {
    const command = cmd || input.trim();
    if (!command) return;
    const result = await onCommand(command);
    if (result) {
      setHistory(prev => [...prev, { command, result }]);
      setLastResult(result);
    }
    setInput('');
  };

  return (
    <div>
      <div className="panel">
        <div className="panel-title">Natural Language Editor</div>
        <div className="panel-subtitle">
          Tell the AI what to change — it understands interior design language
        </div>

        <div className="nlp-input-row">
          <input
            className="input"
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleSubmit()}
            placeholder='e.g. "Move sofa closer to fireplace" or "Use warmer lighting"'
            disabled={loading || !sessionId}
          />
          <button
            className="btn btn-primary"
            onClick={() => handleSubmit()}
            disabled={loading || !input.trim() || !sessionId}
          >
            Apply
          </button>
          <button
            className="btn btn-secondary"
            onClick={onUndo}
            disabled={loading || !sessionId || history.length === 0}
          >
            Undo
          </button>
        </div>

        <div style={{ marginBottom: 16 }}>
          <div className="label" style={{ marginBottom: 8 }}>Suggestions</div>
          <div className="suggestion-chips">
            {COMMAND_SUGGESTIONS.map((s, i) => (
              <span
                key={i}
                className="chip"
                onClick={() => handleSubmit(s)}
              >
                {s}
              </span>
            ))}
          </div>
        </div>

        {lastResult && (
          <div style={{ padding: '12px 16px', background: 'var(--surface-elevated)', borderRadius: 8, fontSize: 13, marginBottom: 16 }}>
            <div style={{ color: 'var(--success)', marginBottom: 4 }}>✓ {lastResult.description}</div>
            <div style={{ color: 'var(--text-secondary)' }}>
              Intent: <strong>{lastResult.intent_type}</strong> ·
              Confidence: {(lastResult.intent_confidence * 100).toFixed(0)}% ·
              Furniture: {lastResult.furniture_count}
            </div>
            {lastResult.violations?.length > 0 && (
              <div style={{ color: 'var(--danger)', marginTop: 4 }}>
                ⚠ {lastResult.violations.length} violation(s)
              </div>
            )}
          </div>
        )}

        {history.length > 0 && (
          <div>
            <div className="label" style={{ marginBottom: 8 }}>Command History</div>
            <div className="command-history">
              {history.slice().reverse().map((h, i) => (
                <div key={i} className="command-history-item">
                  <span style={{ color: 'var(--accent)', marginRight: 8 }}>›</span>
                  {h.command}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {history.length > 0 && (
        <div style={{ marginTop: 20 }}>
          <button
            className="btn btn-primary"
            onClick={() => onRender('preview')}
            disabled={loading}
          >
            Re-render with Changes →
          </button>
        </div>
      )}
    </div>
  );
}
