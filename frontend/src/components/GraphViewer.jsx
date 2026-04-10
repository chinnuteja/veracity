import { useRef, useCallback, useEffect, useState } from 'react'
import ForceGraph2D from 'react-force-graph-2d'

const NODE_TYPE_CONFIG = {
  Product: { shape: 'circle', baseSize: 10, emoji: '🍵' },
  Ingredient: { shape: 'diamond', baseSize: 5, emoji: '🌿' },
  HealthBenefit: { shape: 'circle', baseSize: 5, emoji: '💚' },
  HealthConcern: { shape: 'circle', baseSize: 5, emoji: '🩺' },
  Occasion: { shape: 'circle', baseSize: 5, emoji: '⏰' },
  Category: { shape: 'circle', baseSize: 6, emoji: '📂' },
  UseCase: { shape: 'circle', baseSize: 5, emoji: '🎯' },
}

export default function GraphViewer({ data, onNodeClick, selectedNode }) {
  const fgRef = useRef()
  const [highlightNodes, setHighlightNodes] = useState(new Set())
  const [highlightLinks, setHighlightLinks] = useState(new Set())
  const [hoverNode, setHoverNode] = useState(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })
  const containerRef = useRef()

  // Responsive sizing
  useEffect(() => {
    function updateSize() {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setDimensions({ width: rect.width, height: rect.height })
      }
    }
    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [])

  // Physics engine tweak for dense graphs
  useEffect(() => {
    if (fgRef.current && data) {
      // Push nodes much further apart to untangle the hairball
      fgRef.current.d3Force('charge').strength(-300);
      fgRef.current.d3Force('link').distance(60);
    }
  }, [data]);

  // Build neighbor maps for highlighting
  const neighborMap = useCallback(() => {
    const map = new Map()
    if (!data) return map
    data.links.forEach(link => {
      const src = typeof link.source === 'object' ? link.source.id : link.source
      const tgt = typeof link.target === 'object' ? link.target.id : link.target
      if (!map.has(src)) map.set(src, new Set())
      if (!map.has(tgt)) map.set(tgt, new Set())
      map.get(src).add(tgt)
      map.get(tgt).add(src)
    })
    return map
  }, [data])

  const handleNodeHover = useCallback((node) => {
    setHoverNode(node)
    if (node) {
      const neighbors = neighborMap()
      const connected = neighbors.get(node.id) || new Set()
      setHighlightNodes(new Set([node.id, ...connected]))
      setHighlightLinks(new Set(
        data.links
          .filter(l => {
            const src = typeof l.source === 'object' ? l.source.id : l.source
            const tgt = typeof l.target === 'object' ? l.target.id : l.target
            return src === node.id || tgt === node.id
          })
          .map((_, i) => i)
      ))
    } else {
      setHighlightNodes(new Set())
      setHighlightLinks(new Set())
    }
  }, [data, neighborMap])

  const handleClick = useCallback((node) => {
    if (node && onNodeClick) {
      onNodeClick(node)
    }
    // Center on clicked node
    if (fgRef.current && node) {
      fgRef.current.centerAt(node.x, node.y, 500)
      fgRef.current.zoom(3, 500)
    }
  }, [onNodeClick])

  // Node painting
  const paintNode = useCallback((node, ctx, globalScale) => {
    const config = NODE_TYPE_CONFIG[node.type] || { baseSize: 4 }
    const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(node.id)
    const isSelected = selectedNode && selectedNode.id === node.id
    const isHovered = hoverNode && hoverNode.id === node.id
    
    let alpha = 1;
    if (highlightNodes.size > 0 && !isHighlighted) {
      alpha = 0.05; // Fade unhighlighted nodes almost completely into the background
    }
    
    const size = (node.size || config.baseSize) / globalScale * 3

    ctx.globalAlpha = alpha

    // Glow effect for highlighted nodes
    if (isHovered || isSelected) {
      ctx.shadowColor = node.color
      ctx.shadowBlur = 20
    }

    // Draw node
    ctx.beginPath()
    ctx.arc(node.x, node.y, size, 0, 2 * Math.PI)
    ctx.fillStyle = node.color
    ctx.fill()

    // Selected ring
    if (isSelected) {
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 2 / globalScale
      ctx.stroke()
    }

    ctx.shadowBlur = 0

    // Label (show only for hovered/selected nodes or when very zoomed in to reduce noise)
    const shouldShowLabel = isHovered || isSelected || (globalScale > 2 && isHighlighted);
    if (shouldShowLabel && alpha > 0.1) {
      const label = node.label.length > 25 ? node.label.substring(0, 25) + '…' : node.label
      const fontSize = Math.max(12 / globalScale, 2)
      ctx.font = `${fontSize}px Inter, sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      
      // Black background pill for easier text reading over the links
      const textWidth = ctx.measureText(label).width;
      const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.2); 
      ctx.fillStyle = 'rgba(10, 10, 26, 0.8)';
      ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y + size + fontSize - bckgDimensions[1] / 2, ...bckgDimensions);

      ctx.fillStyle = '#fff'
      ctx.fillText(label, node.x, node.y + size + fontSize)
    }

    ctx.globalAlpha = 1
  }, [highlightNodes, selectedNode, hoverNode])

  // Link painting
  const paintLink = useCallback((link, ctx) => {
    const srcId = typeof link.source === 'object' ? link.source.id : link.source
    const tgtId = typeof link.target === 'object' ? link.target.id : link.target
    
    // Only highlight if BOTH ends are in the highlight set
    const isHighlighted = highlightNodes.size > 0 && highlightNodes.has(srcId) && highlightNodes.has(tgtId);

    // If nothing is hovered, draw links very faintly to avoid the hairball effect
    let alpha = 0.02; 
    if (isHighlighted) {
      alpha = 0.8;
    } else if (highlightNodes.size > 0) {
      alpha = 0; // Hide completely when hovering a non-adjacent node
    }

    ctx.globalAlpha = alpha
    ctx.strokeStyle = link.color || '#666'
    ctx.lineWidth = isHighlighted ? 2 : 0.2
    ctx.beginPath()
    const srcCoords = typeof link.source === 'object' ? link.source : { x: 0, y: 0 }
    const tgtCoords = typeof link.target === 'object' ? link.target : { x: 0, y: 0 }
    ctx.moveTo(srcCoords.x, srcCoords.y)
    ctx.lineTo(tgtCoords.x, tgtCoords.y)
    ctx.stroke()
    ctx.globalAlpha = 1
  }, [highlightNodes])

  if (!data) return null

  return (
    <div ref={containerRef} className="graph-viewer">
      <ForceGraph2D
        ref={fgRef}
        graphData={data}
        width={dimensions.width}
        height={dimensions.height}
        backgroundColor="#0a0a1a"
        nodeCanvasObject={paintNode}
        linkCanvasObject={paintLink}
        onNodeHover={handleNodeHover}
        onNodeClick={handleClick}
        nodeLabel={n => `${n.type}: ${n.label}`}
        cooldownTicks={100}
        d3AlphaDecay={0.02}
        d3VelocityDecay={0.3}
        enableNodeDrag={true}
        enableZoomPanInteraction={true}
      />

      {/* Legend */}
      <div className="graph-legend">
        <h4>Node Types</h4>
        {Object.entries(NODE_TYPE_CONFIG).map(([type, config]) => (
          <div key={type} className="legend-item">
            <span
              className="legend-dot"
              style={{
                backgroundColor:
                  type === 'Product' ? '#6366F1' :
                  type === 'Ingredient' ? '#F59E0B' :
                  type === 'HealthBenefit' ? '#10B981' :
                  type === 'HealthConcern' ? '#F43F5E' :
                  type === 'Occasion' ? '#0EA5E9' :
                  type === 'Category' ? '#8B5CF6' :
                  '#EC4899'
              }}
            />
            <span>{config.emoji} {type}</span>
          </div>
        ))}
      </div>

      {/* Hover tooltip */}
      {hoverNode && (
        <div className="node-tooltip">
          <strong>{hoverNode.label}</strong>
          <span className="tooltip-type">{hoverNode.type}</span>
          {hoverNode.metadata?.price && (
            <span className="tooltip-price">₹{hoverNode.metadata.price}</span>
          )}
        </div>
      )}
    </div>
  )
}
