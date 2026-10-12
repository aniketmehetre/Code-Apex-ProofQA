import React, { useState } from 'react';
import { MOCK_FINDINGS } from '../mockData';

export const EvidenceView: React.FC = () => {
  const [selectedFinding, setSelectedFinding] = useState(MOCK_FINDINGS[0]);
  const [activeStepIdx, setActiveStepIdx] = useState(3);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div>
        <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Finding & Evidence Inspector</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
          Synchronized, multi-channel evidence: Action Steps, Network I/O, Console output, and Failure Signatures.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '20px' }}>
        {/* Finding List */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--text-secondary)' }}>Verified Findings</h3>
          {MOCK_FINDINGS.map((finding) => (
            <div
              key={finding.id}
              onClick={() => { setSelectedFinding(finding); setActiveStepIdx(finding.steps.length - 1); }}
              style={{
                background: selectedFinding.id === finding.id ? 'var(--bg-card-hover)' : 'var(--bg-card)',
                padding: '16px',
                borderRadius: '8px',
                border: selectedFinding.id === finding.id ? '1px solid var(--accent-green)' : '1px solid var(--border)',
                cursor: 'pointer'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-green)' }} className="font-mono">{finding.id}</span>
                <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '10px', background: 'rgba(16, 185, 129, 0.2)', color: 'var(--accent-green)' }}>
                  Class {finding.oracle_class} • {finding.tier}
                </span>
              </div>
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>{finding.claim}</div>
            </div>
          ))}
        </div>

        {/* Evidence Synchronized Timeline */}
        <div style={{ background: 'var(--bg-card)', borderRadius: '12px', border: '1px solid var(--border)', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Action Step Timeline</h3>
            <div style={{ display: 'flex', gap: '8px', marginTop: '12px', overflowX: 'auto', paddingBottom: '8px' }}>
              {selectedFinding.steps.map((step, idx) => (
                <button
                  key={step.id}
                  onClick={() => setActiveStepIdx(idx)}
                  style={{
                    padding: '8px 14px',
                    borderRadius: '6px',
                    border: activeStepIdx === idx ? '1px solid var(--accent-green)' : '1px solid var(--border)',
                    background: activeStepIdx === idx ? 'rgba(16, 185, 129, 0.15)' : 'var(--bg-secondary)',
                    color: activeStepIdx === idx ? 'var(--accent-green)' : 'var(--text-primary)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    fontWeight: 600,
                    whiteSpace: 'nowrap'
                  }}
                  className="font-mono"
                >
                  Step {idx + 1}: {step.kind.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          {/* Synchronized Channels */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            {/* Channel A: Network Traffic */}
            <div style={{ background: 'var(--bg-secondary)', borderRadius: '8px', padding: '16px', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                Network I/O Capture
              </div>
              <div className="font-mono" style={{ fontSize: '12px', color: 'var(--state-fail)' }}>
                POST {selectedFinding.signature.first_party_endpoint}
              </div>
              <div style={{ fontSize: '12px', marginTop: '4px', color: 'var(--state-fail)', fontWeight: 700 }}>
                Status: {selectedFinding.signature.status} Internal Server Error
              </div>
              <div style={{ fontSize: '11px', marginTop: '6px', color: 'var(--text-muted)' }}>
                Response Body: <code>{`{"detail": "${selectedFinding.signature.message_norm}"}`}</code>
              </div>
            </div>

            {/* Channel B: Browser Console */}
            <div style={{ background: 'var(--bg-secondary)', borderRadius: '8px', padding: '16px', border: '1px solid var(--border)' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                Console & Runtime Telemetry
              </div>
              <div className="font-mono" style={{ fontSize: '12px', color: 'var(--state-fail)' }}>
                [Error] Failed to load resource: the server responded with a status of 500
              </div>
              <div style={{ fontSize: '11px', marginTop: '6px', color: 'var(--text-muted)' }}>
                First-party boundary: <strong>Preserved</strong> (Rule 2/4 compliant)
              </div>
            </div>
          </div>

          {/* Sealed Cryptographic Signature */}
          <div style={{ background: 'rgba(16, 185, 129, 0.05)', borderRadius: '8px', padding: '16px', border: '1px solid rgba(16, 185, 129, 0.2)' }}>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--accent-green)', marginBottom: '4px' }}>
              Failure Signature (Cryptographically Locked)
            </div>
            <pre className="font-mono" style={{ fontSize: '11px', color: 'var(--text-primary)', background: 'var(--bg-primary)', padding: '10px', borderRadius: '6px', overflowX: 'auto' }}>
              {JSON.stringify(selectedFinding.signature, null, 2)}
            </pre>
          </div>
        </div>
      </div>
    </div>
  );
};
