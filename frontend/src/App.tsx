
import { useCallback, useEffect, useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Bell,
  Boxes,
  ChartNoAxesCombined,
  ChevronDown,
  CircleDollarSign,
  LayoutDashboard,
  RefreshCw,
  Search,
  ShieldAlert,
  ShoppingBag,
  Truck,
  Users,
  Wallet,
  CheckCircle2,
  WifiOff,
} from 'lucide-react';

const API = 'http://127.0.0.1:8000';

type DashboardData = {
  sellers: number;
  active_sellers: number;
  listings: number;
  orders: number;
  disputes: number;
  detected_anomalies: number;
  data_mode: string;
};

type Anomaly = {
  scenario: string;
  record_id: number;
  severity: string;
  details: string;
};

const nav = [
  ['Dashboard', LayoutDashboard],
  ['Sellers', Users],
  ['Listings', Boxes],
  ['Orders', ShoppingBag],
  ['Fulfillment', Truck],
  ['Payouts', Wallet],
  ['Commissions', CircleDollarSign],
  ['Disputes', ShieldAlert],
  ['Anomalies', AlertTriangle],
  ['Reports', ChartNoAxesCombined],
] as const;

const titles: Record<string, string> = {
  payout_before_delivery_or_hold_release: 'Payout before delivery / hold release',
  commission_applied_twice: 'Commission applied twice',
  suspended_seller_listing_active: 'Suspended seller has an active listing',
  dispute_not_deducted: 'Dispute deduction missing',
  payout_total_mismatch: 'Payout total mismatch',
};

function formatNumber(value: number | undefined) {
  return value == null ? 'â€”' : value.toLocaleString('en-IN');
}

function friendlyScenario(scenario: string) {
  return titles[scenario] ?? scenario.replace(/_/g, ' ');
}

export default function App() {
  const [page, setPage] = useState('Dashboard');
  const [data, setData] = useState<DashboardData | null>(null);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);
  const [offline, setOffline] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [q, setQ] = useState('');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');

    try {
      const [dashboardResponse, anomaliesResponse] = await Promise.all([
        fetch(`${API}/api/dashboard`),
        fetch(`${API}/api/anomalies`),
      ]);

      if (!dashboardResponse.ok || !anomaliesResponse.ok) {
        throw new Error('The backend returned an unsuccessful response.');
      }

      const dashboard: DashboardData = await dashboardResponse.json();
      const anomalyResult: { count: number; items: Anomaly[] } =
        await anomaliesResponse.json();

      setData(dashboard);
      setAnomalies(anomalyResult.items ?? []);
      setOffline(false);
      setLastUpdated(new Date());
    } catch {
      setOffline(true);
      setError(
        'Could not load live data. Check that the FastAPI backend is running at http://127.0.0.1:8000.',
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const cards = [
    {
      label: 'Total sellers',
      value: formatNumber(data?.sellers),
      Icon: Users,
      color: 'blue',
      note: `${formatNumber(data?.active_sellers)} active sellers`,
    },
    {
      label: 'Total orders',
      value: formatNumber(data?.orders),
      Icon: ShoppingBag,
      color: 'purple',
      note: 'Orders in the database',
    },
    {
      label: 'Product listings',
      value: formatNumber(data?.listings),
      Icon: Boxes,
      color: 'teal',
      note: 'Seller product catalogue',
    },
    {
      label: 'Detected anomalies',
      value: formatNumber(data?.detected_anomalies),
      Icon: AlertTriangle,
      color: 'orange',
      note: 'Rule-based findings',
    },
  ];

  const filteredAnomalies = anomalies.filter((item) => {
    const searchText =
      `${item.scenario} ${item.record_id} ${item.severity} ${item.details}`.toLowerCase();
    return searchText.includes(q.toLowerCase());
  });

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="mark">S</div>
          <div>
            <b>SellerPulse</b>
            <small>OPERATIONS INTELLIGENCE</small>
          </div>
        </div>

        <p className="section">WORKSPACE</p>

        {nav.map(([name, Icon]) => (
          <button
            key={name}
            className={`nav ${page === name ? 'active' : ''}`}
            onClick={() => setPage(name)}
          >
            <Icon size={17} />
            {name}
            {name === 'Anomalies' && (
              <span className="badge">
                {data ? anomalies.length : 'â€”'}
              </span>
            )}
          </button>
        ))}

        <div className="health">
          <i className={offline ? 'red' : ''} />
          <div>
            <b>System status</b>
            <small>
              {loading
                ? 'Connecting..'
                : offline
                  ? 'Backend disconnected'
                  : 'Monitoring ready'}
            </small>
          </div>
        </div>
      </aside>

      <main>
        <header>
          <div className="search">
            <Search size={17} />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search anomaly records"
            />
          </div>

          <div className="right">
            <span className={offline ? 'offline' : 'online'}>
              <i />
              {offline
                ? 'API offline'
                : loading
                  ? 'Connecting'
                  : 'System operational'}
            </span>

            <button
              className="round"
              onClick={() => void refresh()}
              title="Refresh live data"
              disabled={loading}
            >
              <RefreshCw size={16} />
            </button>

            <button className="round" title="Notifications">
              <Bell size={16} />
            </button>

            <div className="avatar">A</div>
            <div className="admin">
              Vijit
              <small>Operations manager</small>
            </div>
            <ChevronDown size={14} />
          </div>
        </header>

        <section className="content">
          <div className="heading">
            <div>
              <div className="eyebrow">
                OPERATIONS OVERVIEW Â· LIVE MONITORING
              </div>
              <h1>
                {page === 'Dashboard' ? 'Good to see you, Vijit.' : page}
                <span>  </span>
              </h1>
              <p>
                Monitor performance, investigate exceptions, and keep every
                payout accountable.
              </p>
            </div>

            <button className="export" onClick={() => window.print()}>
              Export view 
            </button>
          </div>

          {error && (
            <div className="notice">
              <WifiOff size={17} />
              {error}
              <button className="link" onClick={() => void refresh()}>
                Retry
              </button>
            </div>
          )}

          {!offline && !loading && (
            <div className="notice">
              <CheckCircle2 size={17} />
              Connected to the synthetic database. Metrics and anomaly
              findings are loaded from the backend.
            </div>
          )}

          {page === 'Dashboard' && (
            <>
              <div className="cards">
                {cards.map(({ label, value, Icon, color, note }, i) => (
                  <article
                    className={`metric ${color}`}
                    style={{ animationDelay: `${i * 80}ms` }}
                    key={label}
                  >
                    <div className="metric-top">
                      <div className="metric-icon">
                        <Icon size={20} />
                      </div>
                      <span className="trend">
                        {loading ? 'Loading...' : 'Live data'}
                      </span>
                    </div>
                    <small>{label}</small>
                    <strong>{value}</strong>
                    <p>{note}</p>
                  </article>
                ))}
              </div>

              <div className="charts">
                <article className="panel">
                  <div className="panel-head">
                    <div>
                      <h2>Database overview</h2>
                      <p>Current counts returned by the API</p>
                    </div>
                    <span className="select">Live counts</span>
                  </div>

                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Metric</th>
                          <th>Count</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[
                          ['Sellers', data?.sellers],
                          ['Active sellers', data?.active_sellers],
                          ['Product listings', data?.listings],
                          ['Orders', data?.orders],
                          ['Disputes', data?.disputes],
                          ['Detected anomalies', data?.detected_anomalies],
                        ].map(([label, value]) => (
                          <tr key={String(label)}>
                            <td>{label}</td>
                            <td>{formatNumber(value as number | undefined)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="legend">
                    <span>
                      <Activity size={14} /> Last refreshed:{' '}
                      {lastUpdated
                        ? lastUpdated.toLocaleTimeString()
                        : 'Not yet'}
                    </span>
                  </div>
                </article>

                <article className="panel">
                  <div className="panel-head">
                    <div>
                      <h2>Exception command center</h2>
                      <p>Findings from the anomaly detector</p>
                    </div>
                    <button className="link" onClick={() => setPage('Anomalies')}>
                      View all ’
                    </button>
                  </div>

                  {anomalies.slice(0, 5).map((item, i) => (
                    <div className="exception" key={`${item.scenario}-${item.record_id}`}>
                      <div className={`alert-icon s${i}`}>
                        <AlertTriangle size={16} />
                      </div>
                      <div className="excopy">
                        <b>{friendlyScenario(item.scenario)}</b>
                        <small>Record #{item.record_id}</small>
                      </div>
                      <span className={`severity ${item.severity.toLowerCase()}`}>
                        {item.severity}
                      </span>
                    </div>
                  ))}

                  {!loading && anomalies.length === 0 && (
                    <p>No anomalies returned by the API.</p>
                  )}
                </article>
              </div>
            </>
          )}

          {page === 'Anomalies' && (
            <article className="panel">
              <div className="panel-head">
                <div>
                  <h2>Detected anomalies</h2>
                  <p>
                    {filteredAnomalies.length} matching records Â· backend
                    rule-based checks
                  </p>
                </div>
                <button className="link" onClick={() => void refresh()}>
                  <RefreshCw size={14} /> Refresh
                </button>
              </div>

              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Scenario</th>
                      <th>Record ID</th>
                      <th>Severity</th>
                      <th>Details</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAnomalies.map((item) => (
                      <tr key={`${item.scenario}-${item.record_id}`}>
                        <td>{friendlyScenario(item.scenario)}</td>
                        <td className="id">{item.record_id}</td>
                        <td>
                          <span
                            className={`severity ${item.severity.toLowerCase()}`}
                          >
                            {item.severity}
                          </span>
                        </td>
                        <td>{item.details}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {!loading && filteredAnomalies.length === 0 && (
                <p>
                  {anomalies.length
                    ? 'No anomaly records match your search.'
                    : 'No anomaly records are currently available.'}
                </p>
              )}
            </article>
          )}

          {page !== 'Dashboard' && page !== 'Anomalies' && (
            <article className="panel">
              <div className="panel-head">
                <div>
                  <h2>{page} overview</h2>
                  <p>
                    This section is not connected to a dedicated backend
                    endpoint yet.
                  </p>
                </div>
              </div>
              <p>
                The current backend provides dashboard metrics and anomaly
                findings. Detailed {page.toLowerCase()} records will need
                their own API endpoint before they can be displayed here.
              </p>
              <button className="link" onClick={() => setPage('Dashboard')}>
                â† Back to dashboard
              </button>
            </article>
          )}

          {offline && !data && (
            <div className="panel">
              <h2>Waiting for backend</h2>
              <p>
                Start FastAPI, then select Refresh. Live metrics will appear
                when the API responds.
              </p>
            </div>
          )}

          <footer>
            <span>SellerPulse. A Operations Intelligence</span>
            <span>
              <i className={offline ? 'red' : 'green'} />
              {offline
                ? 'API unavailable'
                : data?.data_mode === 'synthetic_database'
                  ? 'Synthetic data. A auditable rules'
                  : 'Backend status unknown'}
            </span>
          </footer>
        </section>
      </main>
    </div>
  );
}

