import React from 'react';

export default function StatsCards({ stats, selectedReason, onSelectReason }) {
  if (!stats) return null;

  const cards = [
    {
      key: 'ALL',
      label: 'Total Discrepancies',
      value: stats.total || 0,
      className: 'stat-card--total',
      icon: '📊',
    },
    {
      key: 'MISSING_IN_SYSTEM_B',
      label: 'Missing in System B',
      value: stats.missing_in_system_b || 0,
      className: 'stat-card--missing',
      icon: '⚠️',
    },
    {
      key: 'ORPHAN_IN_SYSTEM_B',
      label: 'Orphans in System B',
      value: stats.orphan_in_system_b || 0,
      className: 'stat-card--orphan',
      icon: '🔍',
    },
    {
      key: 'DUPLICATE_IN_SYSTEM_B',
      label: 'Duplicates in System B',
      value: stats.duplicate_in_system_b || 0,
      className: 'stat-card--duplicate',
      icon: '📋',
    },
    {
      key: 'VALUE_MISMATCH',
      label: 'Value Mismatches',
      value: stats.value_mismatch || 0,
      className: 'stat-card--mismatch',
      icon: '⚡',
    },
  ];

  return (
    <div className="stats-grid">
      {cards.map((card) => {
        const isActive = selectedReason === card.key;
        return (
          <div
            key={card.key}
            className={`stat-card ${card.className} ${isActive ? 'active' : ''}`}
            onClick={() => onSelectReason && onSelectReason(card.key)}
            style={{ cursor: 'pointer' }}
          >
            <span className="stat-card__icon">{card.icon}</span>
            <div className="stat-card__label">{card.label}</div>
            <div className="stat-card__value">{card.value}</div>
          </div>
        );
      })}
    </div>
  );
}
