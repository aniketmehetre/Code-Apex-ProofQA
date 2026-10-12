import React, { useState } from 'react';
import { RaceView } from './components/RaceView';
import { ExplorerView } from './components/ExplorerView';
import { EvidenceView } from './components/EvidenceView';
import { ShrinkView } from './components/ShrinkView';
import { VerifyView } from './components/VerifyView';
import { BenchScoreboardView } from './components/BenchScoreboardView';
import { ReviewQueueView } from './components/ReviewQueueView';

type TabType = 'race' | 'explorer' | 'evidence' | 'shrink' | 'verify' | 'bench' | 'review';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('race');
  const [isLive, setIsLive] = useState(false);

  const tabs: Array<{ id: TabType; label: string }> = [
    { id: 'race', label: 'Race Lane' },
    { id: 'explorer', label: 'State Graph' },
    { id: 'evidence', label: 'Finding & Evidence' },
    { id: 'shrink', label: 'Trace Shrink (ddmin)' },
    { id: 'verify', label: 'Verify & Tamper Demo' },
    { id: 'bench', label: 'ProofBench Scoreboard' },
    { id: 'review', label: 'Review & Suppression' },
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column', background: 'var(--bg-primary)' }}>
      {/* Top Header */}
      <header
        style={{
          background: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border)',
          padding: '16px 32px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          position: 'sticky',
          top: 0,
          zIndex: 50
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ width: '16px', height: '16px', borderRadius: '4px', background: 'var(--accent-green)', boxShadow: '0 0 10px var(--accent-green)' }} />
            <span style={{ fontSize: '20px', fontWeight: 800, letterSpacing: '-0.5px' }}>ProofQA 2.0</span>
          </div>
          <span style={{ fontSize: '12px', padding: '3px 8px', borderRadius: '4px', background: 'var(--bg-card)', color: 'var(--accent-green)', border: '1px solid var(--border)', fontWeight: 600 }}>
            Autonomous QA Control Plane
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {/* Live vs Mock Mode Switcher */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'var(--bg-card)', padding: '4px 8px', borderRadius: '8px', border: '1px solid var(--border)' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Mode:</span>
            <button
              onClick={() => setIsLive(false)}
              style={{
                background: !isLive ? 'var(--border)' : 'transparent',
                color: !isLive ? 'var(--text-primary)' : 'var(--text-muted)',
                border: 'none',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Standalone Mock
            </button>
            <button
              onClick={() => setIsLive(true)}
              style={{
                background: isLive ? 'var(--accent-green)' : 'transparent',
                color: isLive ? '#000' : 'var(--text-muted)',
                border: 'none',
                padding: '4px 10px',
                borderRadius: '6px',
                fontSize: '12px',
                fontWeight: 700,
                cursor: 'pointer'
              }}
            >
              Live API / SSE
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: 'var(--text-secondary)' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: isLive ? 'var(--accent-green)' : 'var(--text-muted)' }} />
            <span>{isLive ? 'Connected to FastAPI' : 'Offline Mock'}</span>
          </div>
        </div>
      </header>

      {/* Tab Navigation */}
      <nav
        style={{
          background: 'var(--bg-secondary)',
          borderBottom: '1px solid var(--border)',
          padding: '0 32px',
          display: 'flex',
          gap: '8px'
        }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: '14px 18px',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid var(--accent-green)' : '2px solid transparent',
              background: 'transparent',
              color: activeTab === tab.id ? 'var(--accent-green)' : 'var(--text-secondary)',
              fontWeight: activeTab === tab.id ? 700 : 500,
              fontSize: '14px',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {/* Main Screen Content */}
      <main style={{ flex: 1, padding: '32px', maxWidth: '1400px', width: '100%', margin: '0 auto' }}>
        {activeTab === 'race' && <RaceView isLive={isLive} />}
        {activeTab === 'explorer' && <ExplorerView />}
        {activeTab === 'evidence' && <EvidenceView />}
        {activeTab === 'shrink' && <ShrinkView />}
        {activeTab === 'verify' && <VerifyView isLive={isLive} />}
        {activeTab === 'bench' && <BenchScoreboardView isLive={isLive} />}
        {activeTab === 'review' && <ReviewQueueView isLive={isLive} />}
      </main>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--border)', padding: '16px 32px', textAlign: 'center', fontSize: '12px', color: 'var(--text-muted)' }}>
        ProofQA 2.0 • Team VOID MAIN • Code Apex Hackathon • Pairwise Deterministic Verification Native Architecture
      </footer>
    </div>
  );
};
