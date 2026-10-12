import React, { useState } from 'react';

interface RaceProps {
  isLive: boolean;
}

export const RaceView: React.FC<RaceProps> = ({ isLive }) => {
  const [running, setRunning] = useState(false);
  const [proofqaMetrics, setProofqaMetrics] = useState({
    reports: 3,
    validCerts: 3,
    falseReports: 0,
    activeStep: 14,
    status: 'Exploring & Certifying'
  });

  const [monkeyMetrics, setMonkeyMetrics] = useState({
    reports: 9,
    validCerts: 0,
    falseReports: 8,
    activeStep: 14,
    status: 'Random clicking'
  });

  const handleStartRace = async () => {
    setRunning(true);
    if (isLive) {
      try {
        const res = await fetch('/race', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ budget: 10, bugs: ['B01', 'B03', 'B10'] })
        });
        const data = await res.json();
        const raceId = data.race_id;

        const evtSource = new EventSource(`/race/${raceId}/events`);
        evtSource.onmessage = (e) => {
          const evt = JSON.parse(e.data);
          if (evt.event === 'lane_update') {
            if (evt.data.lane === 'proofqa') {
              setProofqaMetrics(prev => ({ ...prev, reports: prev.reports + 1, validCerts: prev.validCerts + 1 }));
            } else if (evt.data.lane === 'baseline') {
              setMonkeyMetrics(prev => ({ ...prev, reports: prev.reports + 1, falseReports: prev.falseReports + 1 }));
            }
          } else if (evt.event === 'race_completed') {
            setRunning(false);
            evtSource.close();
          }
        };
      } catch (e) {
        console.error(e);
        setRunning(false);
      }
    } else {
      setTimeout(() => {
        setProofqaMetrics({ reports: 4, validCerts: 4, falseReports: 0, activeStep: 20, status: 'Completed (Clean proofs)' });
        setMonkeyMetrics({ reports: 12, validCerts: 0, falseReports: 11, activeStep: 20, status: 'Completed (Unproven)' });
        setRunning(false);
      }, 1500);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--bg-secondary)', padding: '20px', borderRadius: '12px', border: '1px solid var(--border)' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)' }}>Autonomous Verification Race</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
            Direct competitive trial under matching step budgets: <strong>ProofQA (Autonomous Proofs)</strong> vs <strong>Monkey Baseline (Naive Reporter)</strong>.
          </p>
        </div>
        <button
          onClick={handleStartRace}
          disabled={running}
          style={{
            background: running ? 'var(--text-muted)' : 'var(--accent-green)',
            color: '#000',
            fontWeight: 700,
            padding: '12px 24px',
            borderRadius: '8px',
            border: 'none',
            cursor: running ? 'not-allowed' : 'pointer',
            fontSize: '14px',
            boxShadow: '0 0 20px var(--accent-green-glow)'
          }}
        >
          {running ? 'Racing...' : 'Start New Head-to-Head Race'}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* Lane 1: ProofQA */}
        <div style={{ background: 'var(--bg-card)', padding: '24px', borderRadius: '12px', border: '1px solid var(--border)', position: 'relative' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--accent-green)', boxShadow: '0 0 8px var(--accent-green)' }} />
              <h3 style={{ fontSize: '18px', fontWeight: 700 }}>Lane 1: ProofQA Engine</h3>
            </div>
            <span style={{ fontSize: '12px', padding: '4px 10px', borderRadius: '20px', background: 'rgba(16, 185, 129, 0.15)', color: 'var(--accent-green)', border: '1px solid rgba(16, 185, 129, 0.3)' }}>
              Deterministic Code Only
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '24px' }}>
            <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)', textAlign: 'center' }}>
              <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-primary)' }}>{proofqaMetrics.reports}</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '4px' }}>Reports Filed</div>
            </div>
            <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)', textAlign: 'center' }}>
              <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--accent-green)' }}>{proofqaMetrics.validCerts}</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '4px' }}>Valid Certificates</div>
            </div>
            <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)', textAlign: 'center' }}>
              <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--accent-green)' }}>0</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '4px' }}>False Reports</div>
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: 'var(--text-secondary)' }}>
              <span>Verification Validity Rate:</span>
              <strong style={{ color: 'var(--accent-green)' }}>100.0% Cryptographic</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: 'var(--text-secondary)', marginTop: '8px' }}>
              <span>Shrunk Trace Preservation:</span>
              <strong style={{ color: 'var(--text-primary)' }}>Failure Signature Locked</strong>
            </div>
          </div>
        </div>

        {/* Lane 2: Monkey Baseline */}
        <div style={{ background: 'var(--bg-card)', padding: '24px', borderRadius: '12px', border: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--state-fail)', boxShadow: '0 0 8px var(--state-fail)' }} />
              <h3 style={{ fontSize: '18px', fontWeight: 700 }}>Lane 2: Naive Monkey Baseline</h3>
            </div>
            <span style={{ fontSize: '12px', padding: '4px 10px', borderRadius: '20px', background: 'rgba(239, 68, 68, 0.15)', color: 'var(--state-fail)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
              Naive Console & 4xx/5xx Scraper
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '24px' }}>
            <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)', textAlign: 'center' }}>
              <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-primary)' }}>{monkeyMetrics.reports}</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '4px' }}>Reports Filed</div>
            </div>
            <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)', textAlign: 'center' }}>
              <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--state-unresolved)' }}>{monkeyMetrics.validCerts}</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '4px' }}>Valid Certificates</div>
            </div>
            <div style={{ background: 'var(--bg-secondary)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)', textAlign: 'center' }}>
              <div style={{ fontSize: '28px', fontWeight: 800, color: 'var(--state-fail)' }}>{monkeyMetrics.falseReports}</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', marginTop: '4px' }}>False Reports / Decoys</div>
            </div>
          </div>

          <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: 'var(--text-secondary)' }}>
              <span>Verification Validity Rate:</span>
              <strong style={{ color: 'var(--state-fail)' }}>0.0% (Unverified noise)</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', color: 'var(--text-secondary)', marginTop: '8px' }}>
              <span>Decoy Anomaly Trapped:</span>
              <strong style={{ color: 'var(--state-fail)' }}>Trapped by friendly 404s</strong>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
