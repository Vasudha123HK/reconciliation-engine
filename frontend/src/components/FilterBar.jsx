import React from 'react';

export default function FilterBar({
  organizations,
  selectedOrg,
  onSelectOrg,
  selectedReason,
  onSelectReason,
  sortAsc,
  onToggleSort,
}) {
  return (
    <div className="filter-bar">
      <div className="filter-group">
        <label htmlFor="org-select">Tenant / Organization</label>
        <select
          id="org-select"
          value={selectedOrg}
          onChange={(e) => onSelectOrg(e.target.value)}
        >
          {organizations.map((org) => (
            <option key={org.org_id} value={org.org_id}>
              {org.org_name} ({org.org_id})
            </option>
          ))}
        </select>
      </div>

      <div className="filter-group">
        <label htmlFor="reason-select">Discrepancy Reason</label>
        <select
          id="reason-select"
          value={selectedReason}
          onChange={(e) => onSelectReason(e.target.value)}
        >
          <option value="ALL">All Discrepancy Types</option>
          <option value="MISSING_IN_SYSTEM_B">Missing in System B</option>
          <option value="ORPHAN_IN_SYSTEM_B">Orphan in System B</option>
          <option value="DUPLICATE_IN_SYSTEM_B">Duplicate in System B</option>
          <option value="VALUE_MISMATCH">Value Mismatch</option>
        </select>
      </div>

      <div className="filter-group" style={{ flex: '0 0 auto', minWidth: 'auto' }}>
        <label>&nbsp;</label>
        <button
          type="button"
          className={`sort-button ${!sortAsc ? 'sort-button--desc' : ''}`}
          onClick={onToggleSort}
          title="Toggle record ID sort order"
        >
          <span className="sort-icon">▲</span>
          Sort: {sortAsc ? 'Ascending' : 'Descending'}
        </button>
      </div>
    </div>
  );
}
