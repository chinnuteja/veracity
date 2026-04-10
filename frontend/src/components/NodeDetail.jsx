export default function NodeDetail({ node, graphData, onClose }) {
  if (!node) return null

  // Find all connections for this node
  const connections = graphData.links
    .filter(l => {
      const src = typeof l.source === 'object' ? l.source.id : l.source
      const tgt = typeof l.target === 'object' ? l.target.id : l.target
      return src === node.id || tgt === node.id
    })
    .map(l => {
      const src = typeof l.source === 'object' ? l.source.id : l.source
      const tgt = typeof l.target === 'object' ? l.target.id : l.target
      const connectedId = src === node.id ? tgt : src
      const connectedNode = graphData.nodes.find(n => n.id === connectedId)
      return {
        type: l.type,
        label: l.label,
        node: connectedNode,
      }
    })
    .filter(c => c.node)

  // Group connections by relationship type
  const grouped = {}
  connections.forEach(c => {
    if (!grouped[c.type]) grouped[c.type] = []
    grouped[c.type].push(c)
  })

  const isProduct = node.type === 'Product'

  return (
    <div className="node-detail">
      <div className="node-detail-header">
        <div>
          <h3>{node.label}</h3>
          <span className="node-type-badge" style={{ backgroundColor: node.color }}>
            {node.type}
          </span>
        </div>
        <button className="close-btn" onClick={onClose}>✕</button>
      </div>

      {isProduct && node.metadata?.image_url && (
        <img
          src={node.metadata.image_url}
          alt={node.label}
          className="product-image"
          onError={(e) => e.target.style.display = 'none'}
        />
      )}

      {isProduct && (
        <div className="product-meta">
          {node.metadata?.price > 0 && (
            <div className="meta-item">
              <span className="meta-label">Price</span>
              <span className="meta-value">₹{node.metadata.price}</span>
            </div>
          )}
          {node.metadata?.compare_at_price && (
            <div className="meta-item">
              <span className="meta-label">MRP</span>
              <span className="meta-value strikethrough">₹{node.metadata.compare_at_price}</span>
            </div>
          )}
          {node.metadata?.url && (
            <a href={node.metadata.url} target="_blank" rel="noopener noreferrer" className="product-link">
              View on Blue Tea →
            </a>
          )}
        </div>
      )}

      <div className="connections-list">
        <h4>Connections ({connections.length})</h4>
        {Object.entries(grouped).map(([relType, items]) => (
          <div key={relType} className="connection-group">
            <div className="connection-type">{relType.replace(/_/g, ' ')}</div>
            {items.map((item, i) => (
              <div key={i} className="connection-item">
                <span
                  className="connection-dot"
                  style={{ backgroundColor: item.node.color }}
                />
                <span className="connection-name">{item.node.label}</span>
                <span className="connection-node-type">{item.node.type}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
