import React, { useState } from 'react';
import { MOCK_GRAPH_NODES, MOCK_GRAPH_EDGES } from '../mockData';

export const ExplorerView: React.FC = () => {
  const [selectedNode, setSelectedNode] = useState<string | null>("node_cart");

  const currentNode = MOCK_GRAPH_NODES.find(n => n.id === selectedNode);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '20px', fontWeight: 700 }}>Autonomous State Graph Explorer</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
            Live NetworkX state machine tracking deterministic transitions, exploration frontiers, and discovered bugs.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '16px', fontSize: '13px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--accent-green)' }} />
            <span>Visited State</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: 'var(--state-fail)' }} />
            <span>Bug Sighting (Oracle Trigger)</span>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px' }}>
        {/* SVG State Graph Canvas */}
        <div style={{ background: 'var(--bg-card)', borderRadius: '12px', border: '1px solid var(--border)', padding: '20px', height: '420px', position: 'relative' }}>
          <svg width="100%" height="100%" viewBox="0 0 720 360">
            {/* Draw Edges */}
            {MOCK_GRAPH_EDGES.map((edge, idx) => {
              const src = MOCK_GRAPH_NODES.find(n => n.id === edge.from);
              const dst = MOCK_GRAPH_NODES.find(n => n.id === edge.to);
              if (!src || !dst) return null;
              return (
                <g key={idx}>
                  <line
                    x1={src.x}
                    y1={src.y}
                    x2={dst.x}
                    y2={dst.y}
                    stroke="var(--border)"
                    strokeWidth="2"
                    strokeDasharray="4 2"
                  />
                  <circle cx={(src.x + dst.x) / 2} cy={(src.y + dst.y) / 2} r="3" fill="var(--text-muted)" />
                </g>
              );
            })}

            {/* Draw Nodes */}
            {MOCK_GRAPH_NODES.map((node) => {
              const isSelected = selectedNode === node.id;
              return (
                <g
                  key={node.id}
                  onClick={() => setSelectedNode(node.id)}
                  style={{ cursor: 'pointer' }}
                >
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r={isSelected ? "26" : "22"}
                    fill={node.hasBug ? "rgba(239, 68, 68, 0.2)" : "rgba(16, 185, 129, 0.15)"}
                    stroke={node.hasBug ? "var(--state-fail)" : "var(--accent-green)"}
                    strokeWidth={isSelected ? "3" : "2"}
                  />
                  <circle
                    cx={node.x}
                    cy={node.y}
                    r="8"
                    fill={node.hasBug ? "var(--state-fail)" : "var(--accent-green)"}
                  />
                  <text
                    x={node.x}
                    y={node.y + 36}
                    textAnchor="middle"
                    fill="var(--text-primary)"
                    fontSize="11"
                    fontWeight="600"
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        {/* Node Inspector Panel */}
        <div style={{ background: 'var(--bg-card)', borderRadius: '12px', border: '1px solid var(--border)', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
            State Node Inspector
          </h3>

          {currentNode ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', fontSize: '14px' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>URI / Identifier:</span>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }} className="font-mono">
                  {currentNode.label}
                </div>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Visit Frequency:</span>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginTop: '2px' }}>
                  {currentNode.visits} transitions
                </div>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Bug Invariant Status:</span>
                <div style={{ marginTop: '4px' }}>
                  {currentNode.hasBug ? (
                    <span style={{ padding: '4px 10px', borderRadius: '12px', background: 'rgba(239, 68, 68, 0.2)', color: 'var(--state-fail)', fontWeight: 700, fontSize: '12px' }}>
                      BUG SIGHTING (B01 ZeroQuantityException)
                    </span>
                  ) : (
                    <span style={{ padding: '4px 10px', borderRadius: '12px', background: 'rgba(16, 185, 129, 0.15)', color: 'var(--accent-green)', fontWeight: 600, fontSize: '12px' }}>
                      Clean Behavioral Pass
                    </span>
                  )}
                </div>
              </div>
              <div style={{ marginTop: '8px', padding: '12px', background: 'var(--bg-secondary)', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '12px' }}>
                <div style={{ color: 'var(--text-secondary)' }}>Rule-Based Trap Check:</div>
                <div style={{ color: 'var(--accent-green)', marginTop: '4px', fontWeight: 600 }}>PASSED (Zero infinite loops)</div>
              </div>
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', fontSize: '14px' }}>Select any graph node to inspect state transitions.</p>
          )}
        </div>
      </div>
    </div>
  );
};
