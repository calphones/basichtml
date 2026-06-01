import { useState, useCallback } from 'react';
import UploadPanel from './components/UploadPanel';
import StyleSelector from './components/StyleSelector';
import DesignCanvas from './components/DesignCanvas';
import RenderViewer from './components/RenderViewer';
import NLPEditor from './components/NLPEditor';
import MaterialBoard from './components/MaterialBoard';
import {
  parseFloorPlan, generateDesign, submitRender, runRender,
  applyCommand, undoCommand, getHealth,
} from './api/client';
import './styles.css';

const TABS = ['upload', 'style', 'design', 'render', 'edit', 'materials'];

export default function App() {
  const [tab, setTab] = useState('upload');
  const [sessionId, setSessionId] = useState('');
  const [filePath, setFilePath] = useState('');
  const [style, setStyle] = useState('modern_organic');
  const [prompt, setPrompt] = useState('');
  const [designData, setDesignData] = useState(null);
  const [renderJob, setRenderJob] = useState(null);
  const [renderUrl, setRenderUrl] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [violations, setViolations] = useState([]);
  const [furnitureCount, setFurnitureCount] = useState(0);

  const handleUpload = useCallback(({ sessionId: sid, filePath: fp }) => {
    setSessionId(sid);
    setFilePath(fp);
    setTab('style');
  }, []);

  const handleParsePlan = useCallback(async () => {
    if (!filePath || !sessionId) return;
    setLoading(true);
    setError('');
    try {
      const result = await parseFloorPlan(sessionId, filePath);
      setDesignData(result);
      setTab('style');
    } catch (e) {
      setError(`Parse error: ${e.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  }, [filePath, sessionId]);

  const handleGenerate = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    setError('');
    try {
      const result = await generateDesign(sessionId, { style, prompt, familyFriendly: true });
      setDesignData(result);
      setFurnitureCount(result.furniture_count);
      setViolations(result.violations || []);
      setTab('design');
    } catch (e) {
      setError(`Design error: ${e.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  }, [sessionId, style, prompt]);

  const handleRender = useCallback(async (mode = 'preview', cameraPreset = null) => {
    if (!sessionId) return;
    setLoading(true);
    setError('');
    setRenderUrl(null);
    try {
      const job = await submitRender(sessionId, { mode, cameraPreset });
      setRenderJob(job);
      const finished = await runRender(job.job_id);
      setRenderJob(finished);
      if (finished.output_url) {
        setRenderUrl(`http://localhost:8000${finished.output_url}`);
      }
      setTab('render');
    } catch (e) {
      setError(`Render error: ${e.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const handleCommand = useCallback(async (command) => {
    if (!sessionId) return;
    setLoading(true);
    setError('');
    try {
      const result = await applyCommand(sessionId, command);
      setFurnitureCount(result.furniture_count);
      setViolations(result.violations || []);
      return result;
    } catch (e) {
      setError(`Edit error: ${e.response?.data?.detail || e.message}`);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  const handleUndo = useCallback(async () => {
    if (!sessionId) return;
    setLoading(true);
    try {
      await undoCommand(sessionId);
    } catch (e) {
      setError(`Undo error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">Interior AI</div>
        <nav className="tab-nav">
          {TABS.map(t => (
            <button
              key={t}
              className={`tab-btn ${tab === t ? 'active' : ''}`}
              onClick={() => setTab(t)}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </nav>
        <div className="session-badge">
          {sessionId ? `Session: ${sessionId.slice(0, 8)}` : 'No session'}
        </div>
      </header>

      {error && (
        <div className="error-banner">
          {error}
          <button onClick={() => setError('')}>×</button>
        </div>
      )}
      {loading && <div className="loading-bar"><div className="loading-progress" /></div>}

      <main className="app-main">
        {tab === 'upload' && (
          <UploadPanel
            sessionId={sessionId}
            onUpload={handleUpload}
            onParsePlan={handleParsePlan}
          />
        )}
        {tab === 'style' && (
          <StyleSelector
            style={style}
            prompt={prompt}
            onStyleChange={setStyle}
            onPromptChange={setPrompt}
            onGenerate={handleGenerate}
            loading={loading}
          />
        )}
        {tab === 'design' && (
          <DesignCanvas
            designData={designData}
            furnitureCount={furnitureCount}
            violations={violations}
            onRender={handleRender}
            loading={loading}
          />
        )}
        {tab === 'render' && (
          <RenderViewer
            renderUrl={renderUrl}
            renderJob={renderJob}
            onReRender={handleRender}
            loading={loading}
          />
        )}
        {tab === 'edit' && (
          <NLPEditor
            sessionId={sessionId}
            furnitureCount={furnitureCount}
            onCommand={handleCommand}
            onUndo={handleUndo}
            onRender={handleRender}
            loading={loading}
          />
        )}
        {tab === 'materials' && (
          <MaterialBoard style={style} />
        )}
      </main>
    </div>
  );
}
