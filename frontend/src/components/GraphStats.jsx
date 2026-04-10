export default function GraphStats({ stats }) {
  if (!stats) return null

  const discoveredEdges = stats.discovered_relationships || 0
  const totalEdges = stats.total_edges || 1
  const discoveredPct = Math.round((discoveredEdges / totalEdges) * 100)

  return (
    <div className="stats-bar">
      <div className="stat-item">
        <span className="stat-value">{stats.total_nodes}</span>
        <span className="stat-label">Nodes</span>
      </div>
      <div className="stat-item">
        <span className="stat-value">{stats.total_edges}</span>
        <span className="stat-label">Relationships</span>
      </div>
      <div className="stat-item highlight">
        <span className="stat-value">{discoveredEdges}</span>
        <span className="stat-label">Discovered by Graph</span>
      </div>
      <div className="stat-item highlight">
        <span className="stat-value">{discoveredPct}%</span>
        <span className="stat-label">Hidden in Shopify</span>
      </div>

      {stats.nodes_by_type && (
        <>
          <div className="stat-divider" />
          {Object.entries(stats.nodes_by_type).map(([type, count]) => (
            <div key={type} className="stat-item small">
              <span className="stat-value">{count}</span>
              <span className="stat-label">{type}</span>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
