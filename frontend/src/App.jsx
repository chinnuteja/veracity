import { useState, useEffect } from 'react'
import GraphViewer from './components/GraphViewer'
import QueryDemo from './components/QueryDemo'
import GraphStats from './components/GraphStats'
import NodeDetail from './components/NodeDetail'
import GeoDemo from './components/GeoDemo'
import StoreIngestion from './components/StoreIngestion'
import EmptyState from './components/EmptyState'
import './index.css'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const TABS = [
  { id: 'graph', label: '🔮 Knowledge Graph', icon: '◉' },
  { id: 'query', label: '⚡ Query Demo', icon: '⚡' },
  { id: 'geo', label: '🚀 GEO Optimizer', icon: '🚀' },
  { id: 'ingest', label: '📥 Add Store', icon: '📥' },
]

function App() {
  const [activeTab, setActiveTab] = useState('graph')
  const [graphData, setGraphData] = useState(null)
  const [stats, setStats] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      const [graphRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/graph`).then(r => r.json()),
        fetch(`${API_BASE}/graph/stats`).then(r => r.json()),
      ])
      setGraphData(graphRes)
      setStats(statsRes)
      setError(null)
    } catch (err) {
      setError('Failed to connect to API. Make sure the FastAPI server is running on port 8000.')
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const handleNodeClick = (node) => {
    setSelectedNode(node)
  }

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <h2>Loading Knowledge Graph...</h2>
        <p>Connecting to the Helio Veracity Layer</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-screen">
        <h2>⚠️ Connection Error</h2>
        <p>{error}</p>
        <code>uvicorn backend.main:app --reload --port 8000</code>
      </div>
    )
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="app-header">
        <div className="header-brand">
          <div className="logo-mark">◈</div>
          <div className="header-text">
            <h1>Helio Veracity Layer</h1>
            <p className="header-subtitle">
              Universal Shopify Integration
            </p>
          </div>
        </div>

        <nav className="header-tabs">
          {TABS.map(tab => (
            <button
              key={tab.id}
              className={`tab-btn ${activeTab === tab.id ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      {/* Stats Bar */}
      {stats && <GraphStats stats={stats} />}

      {/* Main Content */}
      <main className="app-main">
        {activeTab === 'graph' && (
          <div className="graph-layout">
            <div className="graph-container">
              {graphData && stats?.total_nodes > 0 ? (
                <GraphViewer
                  data={graphData}
                  onNodeClick={handleNodeClick}
                  selectedNode={selectedNode}
                />
              ) : (
                !loading && <EmptyState onAddStore={() => setActiveTab('ingest')} />
              )}
            </div>
            {selectedNode && (
              <NodeDetail
                node={selectedNode}
                graphData={graphData}
                onClose={() => setSelectedNode(null)}
              />
            )}
          </div>
        )}

        {activeTab === 'query' && (
          <QueryDemo apiBase={API_BASE} />
        )}

        {activeTab === 'geo' && (
          <GeoDemo apiBase={API_BASE} />
        )}

        {activeTab === 'ingest' && (
          <StoreIngestion 
            apiBase={API_BASE} 
            onIngestSuccess={() => {
              fetchData();
              setActiveTab('graph');
            }} 
          />
        )}
      </main>
    </div>
  )
}

export default App
