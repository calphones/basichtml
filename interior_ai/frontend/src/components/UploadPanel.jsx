import { useState, useRef } from 'react';
import { uploadFloorPlan, uploadInspiration, parseFloorPlan } from '../api/client';

const ACCEPTED_PLANS = '.pdf,.png,.jpg,.jpeg,.tiff,.dxf,.ifc';
const ACCEPTED_IMAGES = '.jpg,.jpeg,.png,.webp';

export default function UploadPanel({ sessionId, onUpload, onParsePlan }) {
  const [dragover, setDragover] = useState(false);
  const [uploadedPlan, setUploadedPlan] = useState(null);
  const [uploadedInsp, setUploadedInsp] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const planRef = useRef();
  const inspRef = useRef();

  const handlePlanDrop = async (e) => {
    e.preventDefault();
    setDragover(false);
    const file = e.dataTransfer?.files[0] || e.target?.files[0];
    if (!file) return;
    await uploadPlan(file);
  };

  const uploadPlan = async (file) => {
    setLoading(true);
    setError('');
    try {
      const result = await uploadFloorPlan(file, sessionId);
      setUploadedPlan(result);
      onUpload({ sessionId: result.session_id, filePath: result.file_path });
    } catch (e) {
      setError(`Upload failed: ${e.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const uploadInsp = async (file) => {
    setLoading(true);
    setError('');
    try {
      const result = await uploadInspiration(file, uploadedPlan?.session_id || sessionId);
      setUploadedInsp(result);
    } catch (e) {
      setError(`Upload failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleParse = async () => {
    if (!uploadedPlan) return;
    setLoading(true);
    setError('');
    try {
      const result = await parseFloorPlan(uploadedPlan.session_id, uploadedPlan.file_path);
      onParsePlan && onParsePlan(result);
    } catch (e) {
      setError(`Parse failed: ${e.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="panel">
        <div className="panel-title">Upload Floor Plan</div>
        <div className="panel-subtitle">
          Supported: PDF, PNG, JPG, DXF (AutoCAD), IFC (BIM) · Max 100 MB
        </div>

        {error && <div style={{ color: '#f08080', marginBottom: 16, fontSize: 14 }}>{error}</div>}

        {!uploadedPlan ? (
          <div
            className={`dropzone ${dragover ? 'dragover' : ''}`}
            onDrop={handlePlanDrop}
            onDragOver={(e) => { e.preventDefault(); setDragover(true); }}
            onDragLeave={() => setDragover(false)}
            onClick={() => planRef.current?.click()}
          >
            <div className="dropzone-icon">📐</div>
            <div className="dropzone-title">Drop your floor plan here</div>
            <div className="dropzone-subtitle">or click to browse</div>
            <input
              ref={planRef}
              type="file"
              accept={ACCEPTED_PLANS}
              style={{ display: 'none' }}
              onChange={e => uploadPlan(e.target.files[0])}
            />
          </div>
        ) : (
          <div style={{ padding: '20px', background: 'var(--surface-elevated)', borderRadius: 8 }}>
            <div style={{ color: 'var(--success)', marginBottom: 8 }}>✓ Floor plan uploaded</div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{uploadedPlan.filename}</div>
            <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 4 }}>Type: {uploadedPlan.file_type}</div>
          </div>
        )}
      </div>

      {uploadedPlan && (
        <div className="panel" style={{ marginTop: 20 }}>
          <div className="panel-title" style={{ fontSize: 16 }}>Inspiration Image (optional)</div>
          <div className="panel-subtitle">Upload a room photo or design inspiration to extract palette and style</div>

          {uploadedInsp ? (
            <div style={{ fontSize: 13, color: 'var(--success)' }}>✓ {uploadedInsp.filename}</div>
          ) : (
            <button
              className="btn btn-secondary"
              onClick={() => inspRef.current?.click()}
              disabled={loading}
            >
              + Add Inspiration Image
            </button>
          )}
          <input
            ref={inspRef}
            type="file"
            accept={ACCEPTED_IMAGES}
            style={{ display: 'none' }}
            onChange={e => uploadInsp(e.target.files[0])}
          />
        </div>
      )}

      {uploadedPlan && (
        <div style={{ marginTop: 24, display: 'flex', gap: 12 }}>
          <button
            className="btn btn-primary"
            onClick={handleParse}
            disabled={loading}
            style={{ fontSize: 15, padding: '12px 28px' }}
          >
            {loading ? 'Analysing…' : 'Analyse Floor Plan →'}
          </button>
        </div>
      )}
    </div>
  );
}
