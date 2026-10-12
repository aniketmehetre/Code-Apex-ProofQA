import React, { useState } from 'react';

interface ShrinkStep {
  idx: number;
  label: string;
  state: 'green' | 'red' | 'grey';
  description: string;
}

export const ShrinkView: React.FC = () => {
  const [steps, setSteps] = useState<ShrinkStep[]>([
    { idx: 1, label: "GOTO /", state: "green", description: "Required initial catalog navigation" },
    { idx: 2, label: "SCROLL down", state: "grey", description: "Discarded: no-op / non-essential scroll" },
    { idx: 3, label: "HOVER banner", state: "grey", description: "Discarded: volatile decoration" },
    { idx: 4, label: "CLICK Category Audio", state: "grey", description: "Discarded: unneeded filter" },
    { idx: 5, label: "CLICK Headphones", state: "green", description: "Required: opens target product modal" },
    { idx: 6, label: "CLICK Reviews Tab", state: "grey", description: "Discarded: unrelated tab change" },
    { idx: 7, label: "FILL Review text", state: "grey", description: "Discarded: unsubmitted input" },
    { idx: 8, label: "FILL Qty '0'", state: "red", description: "Trigger Core: Level 3 boundary value shrinking" },
    { idx: 9, label: "HOVER Help icon", state: "grey", description: "Discarded: no-op event" },
    { idx: 10, label: "CLICK Confirm Add", state: "green", description: "Required: invokes /api/cart" },
    { idx: 11, label: "SCROLL footer", state: "grey", description: "Discarded: trailing navigation" },
    { idx: 12, label: "RELOAD page", state: "grey", description: "Discarded: post-failure action" }
  ]);

  const [animating, setAnimating] = useState(false);

  const handleSimulateShrink = () => {
    setAnimating(true);
    // Reset all to grey then resolve sequentially
    setSteps(prev => prev.map(s => ({ ...s, state: 'grey' })));
    setTimeout(() => {
      setSteps(prev => prev.map(s => {
        if (s.idx === 8) return { ...s, state: 'red' };
        if ([1, 5, 10].includes(s.idx)) return { ...s, state: 'green' };
        return { ...s, state: 'grey' };
      }));
      setAnimating(false);
    }, 1000);
  };

  const reducedCount = steps.filter(s => s.state === 'green' || s.state === 'red').length;
  const reductionPct = Math.round(((steps.length - reducedCount) / steps.length) * 100);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Three-Valued Delta Debugging (Shrink)</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
            Multi-level trace reduction with signature-locking: Level 1 State-Drop, Level 2 ddmin, Level 3 Value Shrinking.
          </p>
        </div>
        <button
          onClick={handleSimulateShrink}
          disabled={animating}
          style={{
            background: 'var(--accent-green)',
            color: '#000',
            fontWeight: 700,
            padding: '10px 20px',
            borderRadius: '8px',
            border: 'none',
            cursor: 'pointer',
            fontSize: '13px'
          }}
        >
          {animating ? 'Shrinking...' : 'Run Shrink Demonstration'}
        </button>
      </div>

      {/* Metrics Banner */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
        <div style={{ background: 'var(--bg-card)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Original Trace Steps</div>
          <div style={{ fontSize: '24px', fontWeight: 800, marginTop: '4px' }}>12 steps</div>
        </div>
        <div style={{ background: 'var(--bg-card)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Shrunk Minimal Core</div>
          <div style={{ fontSize: '24px', fontWeight: 800, marginTop: '4px', color: 'var(--accent-green)' }}>{reducedCount} steps</div>
        </div>
        <div style={{ background: 'var(--bg-card)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Step Reduction Ratio</div>
          <div style={{ fontSize: '24px', fontWeight: 800, marginTop: '4px', color: 'var(--accent-green)' }}>{reductionPct}%</div>
        </div>
        <div style={{ background: 'var(--bg-card)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Signature Preservation</div>
          <div style={{ fontSize: '24px', fontWeight: 800, marginTop: '4px', color: 'var(--accent-green)' }}>100% Locked</div>
        </div>
      </div>

      {/* Action Blocks Visual Matrix */}
      <div style={{ background: 'var(--bg-card)', padding: '24px', borderRadius: '12px', border: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700 }}>Trace Action Sequence Blocks</h3>
          <div style={{ display: 'flex', gap: '16px', fontSize: '12px' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: 'var(--state-verified)' }} />
              Green: Essential Action
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: 'var(--state-fail)' }} />
              Red: Trigger Core Value
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <span style={{ width: '12px', height: '12px', borderRadius: '3px', background: 'var(--state-unresolved)' }} />
              Grey: Discarded Noise
            </span>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
          {steps.map(step => {
            const bgColor = step.state === 'green' ? 'rgba(16, 185, 129, 0.2)' :
                            step.state === 'red' ? 'rgba(239, 68, 68, 0.25)' :
                            'rgba(100, 116, 139, 0.15)';
            const borderColor = step.state === 'green' ? 'var(--state-verified)' :
                                step.state === 'red' ? 'var(--state-fail)' :
                                'var(--border)';
            const textColor = step.state === 'green' ? 'var(--accent-green)' :
                              step.state === 'red' ? 'var(--state-fail)' :
                              'var(--text-muted)';
            return (
              <div
                key={step.idx}
                style={{
                  background: bgColor,
                  border: `1px solid ${borderColor}`,
                  borderRadius: '8px',
                  padding: '16px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                  transition: 'all 0.3s ease'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)' }}>BLOCK #{step.idx}</span>
                  <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', background: 'var(--bg-primary)', color: textColor, fontWeight: 700 }}>
                    {step.state.toUpperCase()}
                  </span>
                </div>
                <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }} className="font-mono">
                  {step.label}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                  {step.description}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
