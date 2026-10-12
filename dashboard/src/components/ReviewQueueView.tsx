import React, { useState } from 'react';
import { MOCK_FINDINGS } from '../mockData';

interface ReviewProps {
  isLive: boolean;
}

export const ReviewQueueView: React.FC<ReviewProps> = ({ isLive }) => {
  const [items, setItems] = useState(
    MOCK_FINDINGS.map(f => ({ ...f, status: 'pending' as 'pending' | 'approved' | 'rejected' }))
  );

  const handleAction = async (id: string, action: 'approve' | 'reject') => {
    if (isLive) {
      try {
        await fetch(`/findings/${id}/review`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action, reason: `Human reviewer marked as ${action}` })
        });
      } catch {}
    }
    const newStatus = action === 'approve' ? 'approved' : 'rejected';
    setItems(prev => prev.map(item => item.id === id ? { ...item, status: newStatus } : item));
  };

  const approvedCount = items.filter(i => i.status === 'approved').length;
  const rejectedCount = items.filter(i => i.status === 'rejected').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Human Review & Suppression Queue</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
            Approve verified findings to continuous regression suite; reject non-bugs to create signature-level suppression rules.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <div style={{ background: 'var(--bg-card)', padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '13px' }}>
            Regression Suite: <strong style={{ color: 'var(--accent-green)' }}>{approvedCount} active</strong>
          </div>
          <div style={{ background: 'var(--bg-card)', padding: '8px 16px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '13px' }}>
            Suppressed Signatures: <strong style={{ color: 'var(--state-fail)' }}>{rejectedCount} rules</strong>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {items.map(item => (
          <div
            key={item.id}
            style={{
              background: 'var(--bg-card)',
              borderRadius: '10px',
              border: item.status === 'approved' ? '1px solid var(--accent-green)' :
                      item.status === 'rejected' ? '1px solid var(--state-fail)' :
                      '1px solid var(--border)',
              padding: '20px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}
          >
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px' }}>
                <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--accent-green)' }} className="font-mono">{item.id}</span>
                <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '10px', background: 'rgba(16, 185, 129, 0.15)', color: 'var(--accent-green)' }}>
                  Class {item.oracle_class}
                </span>
                <span style={{ fontSize: '11px', padding: '2px 8px', borderRadius: '10px', background: 'var(--bg-secondary)', color: 'var(--text-muted)' }}>
                  {item.tier}
                </span>
              </div>
              <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>{item.claim}</div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }} className="font-mono">
                {item.signature.first_party_endpoint} • status {item.signature.status} • {item.signature.message_norm}
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px' }}>
              {item.status === 'pending' ? (
                <>
                  <button
                    onClick={() => handleAction(item.id, 'approve')}
                    style={{
                      background: 'var(--accent-green)',
                      color: '#000',
                      fontWeight: 700,
                      padding: '8px 16px',
                      borderRadius: '6px',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: '12px'
                    }}
                  >
                    Approve (Add to Suite)
                  </button>
                  <button
                    onClick={() => handleAction(item.id, 'reject')}
                    style={{
                      background: 'rgba(239, 68, 68, 0.15)',
                      color: 'var(--state-fail)',
                      border: '1px solid var(--state-fail)',
                      fontWeight: 700,
                      padding: '8px 16px',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      fontSize: '12px'
                    }}
                  >
                    Reject (Suppress Signature)
                  </button>
                </>
              ) : (
                <span
                  style={{
                    padding: '6px 14px',
                    borderRadius: '20px',
                    background: item.status === 'approved' ? 'rgba(16, 185, 129, 0.2)' : 'rgba(239, 68, 68, 0.2)',
                    color: item.status === 'approved' ? 'var(--accent-green)' : 'var(--state-fail)',
                    fontWeight: 700,
                    fontSize: '12px',
                    border: `1px solid ${item.status === 'approved' ? 'var(--accent-green)' : 'var(--state-fail)'}`
                  }}
                >
                  {item.status === 'approved' ? 'IN REGRESSION SUITE' : 'SIGNATURE SUPPRESSED'}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
