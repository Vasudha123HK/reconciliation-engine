import React from 'react';

const REASON_LABELS = {
  MISSING_IN_SYSTEM_B: 'Missing in System B',
  ORPHAN_IN_SYSTEM_B: 'Orphan in System B',
  DUPLICATE_IN_SYSTEM_B: 'Duplicate in System B',
  VALUE_MISMATCH: 'Value Mismatch',
};

export default function DiscrepancyTable({ items, loading }) {
  if (loading) {
    return (
      <div className="table-container">
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <div>Loading reconciled discrepancy data...</div>
        </div>
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <div className="table-container">
        <div className="empty-state">
          <div className="empty-state__icon">🎉</div>
          <div className="empty-state__title">No Discrepancies Found</div>
          <div className="empty-state__subtitle">
            All records for this tenant match perfectly according to the selected criteria.
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="table-container">
      <div className="table-header-bar">
        <div className="table-header-bar__title">Audit Discrepancy Log</div>
        <div className="table-header-bar__count">
          Showing {items.length} {items.length === 1 ? 'record' : 'records'}
        </div>
      </div>
      <table className="data-table">
        <thead>
          <tr>
            <th style={{ width: '15%' }}>Record Ref</th>
            <th style={{ width: '22%' }}>Reason</th>
            <th style={{ width: '12%' }}>Location</th>
            <th style={{ width: '12%' }}>Tenant</th>
            <th style={{ width: '18%' }}>System A Value</th>
            <th style={{ width: '21%' }}>System B Value</th>
          </tr>
        </thead>
        <tbody>
          {items.map((row, idx) => {
            const reasonClass = `reason-badge--${row.reason}`;
            const reasonText = REASON_LABELS[row.reason] || row.reason;

            return (
              <tr key={row.id || idx}>
                <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                  {row.record_id}
                </td>
                <td>
                  <span className={`reason-badge ${reasonClass}`}>
                    {reasonText}
                  </span>
                </td>
                <td>{row.location_id || '—'}</td>
                <td>{row.org_id}</td>
                <td className={`value-cell ${!row.system_a_value ? 'value-cell--null' : 'value-cell--highlight'}`}>
                  {row.system_a_value ?? '—'}
                </td>
                <td className={`value-cell ${!row.system_b_value ? 'value-cell--null' : 'value-cell--highlight'}`}>
                  {row.system_b_value ?? '—'}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
