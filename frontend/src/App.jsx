import React, { useState, useEffect, useCallback } from 'react';
import FilterBar from './components/FilterBar';
import StatsCards from './components/StatsCards';
import DiscrepancyTable from './components/DiscrepancyTable';

const API_BASE_URL = 'https://reconciliation-engine-4.onrender.com';

export default function App() {
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedReason, setSelectedReason] = useState('ALL');
  const [sortAsc, setSortAsc] = useState(true);
  const [discrepancies, setDiscrepancies] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/organizations/`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        return res.json();
      })
      .then((data) => {
        const orgs = data.results || [];
        setOrganizations(orgs);
        if (orgs.length > 0) {
          setSelectedOrg(orgs[0].org_id);
        }
      })
      .catch((err) => {
        console.error('Failed to fetch organizations:', err);
        setError('Failed to load organization list. Ensure backend is running.');
        setLoading(false);
      });
  }, []);

  const fetchData = useCallback(() => {
    if (!selectedOrg) return;

    setLoading(true);
    setError(null);

    const sortParam = sortAsc ? 'asc' : 'desc';

    const discUrl =
      `${API_BASE_URL}/api/discrepancies/?org_id=${selectedOrg}&reason=${selectedReason}&sort=${sortParam}`;

    const statsUrl =
      `${API_BASE_URL}/api/stats/?org_id=${selectedOrg}`;

    Promise.all([
      fetch(discUrl).then((r) => r.json()),
      fetch(statsUrl).then((r) => r.json()),
    ])
      .then(([discData, statsData]) => {
        setDiscrepancies(discData.results || []);
        setStats(statsData);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Error fetching data:', err);
        setError('Failed to fetch data for selected tenant.');
        setLoading(false);
      });
  }, [selectedOrg, selectedReason, sortAsc]);

  // rest of your code...

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="header-left">
            <div className="logo-icon">AX</div>
            <div>
              <h1 className="header-title">AdosX Reconciliation Engine</h1>
              <div className="header-subtitle">Cross-System Discrepancy & Audit Dashboard</div>
            </div>
          </div>
          <div className="header-badge">
            Tenant Isolated • SQLite Database
          </div>
        </div>
      </header>

      <main className="main-content">
        {error ? (
          <div className="error-state">
            <div className="error-state__icon">⚠️</div>
            <div className="error-state__title">Connection Error</div>
            <div className="error-state__subtitle">{error}</div>
            <button className="retry-button" onClick={fetchData}>
              Retry Connection
            </button>
          </div>
        ) : (
          <>
            <FilterBar
              organizations={organizations}
              selectedOrg={selectedOrg}
              onSelectOrg={setSelectedOrg}
              selectedReason={selectedReason}
              onSelectReason={setSelectedReason}
              sortAsc={sortAsc}
              onToggleSort={() => setSortAsc((prev) => !prev)}
            />

            <StatsCards
              stats={stats}
              selectedReason={selectedReason}
              onSelectReason={setSelectedReason}
            />

            <DiscrepancyTable items={discrepancies} loading={loading} />
          </>
        )}
      </main>
    </div>
  );
}
