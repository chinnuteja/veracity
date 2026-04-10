import { useState, useEffect } from 'react'

export default function GeoDemo({ apiBase }) {
  const [products, setProducts] = useState([])
  const [selectedProduct, setSelectedProduct] = useState('')
  const [geoData, setGeoData] = useState(null)
  const [llmsTxt, setLlmsTxt] = useState('')
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState(null)

  // Fetch initial product list and llms.txt
  useEffect(() => {
    const fetchInit = async () => {
      try {
        const [prodRes, llmRes] = await Promise.all([
          fetch(`${apiBase}/geo/products`),
          fetch(`${apiBase}/geo/llms-txt`)
        ])
        
        if (prodRes.ok) {
          const prodData = await prodRes.json()
          setProducts(prodData)
          if (prodData.length > 0) {
            setSelectedProduct(prodData[0].id)
          }
        }
        
        if (llmRes.ok) {
          const llmData = await llmRes.json()
          setLlmsTxt(llmData.markdown)
        }
      } catch (err) {
        console.error("Failed to fetch GEO data", err)
        setFetchError("Could not connect to the backend API. Please make sure the server is healthy.")
      } finally {
        setLoading(false)
      }
    }
    fetchInit()
  }, [apiBase])

  // Fetch specific product schemas when selection changes
  useEffect(() => {
    const fetchSchema = async () => {
      if (!selectedProduct) return
      
      try {
        const res = await fetch(`${apiBase}/geo/product/${selectedProduct}`)
        if (res.ok) {
          const data = await res.json()
          setGeoData(data)
        }
      } catch (err) {
        console.error("Failed to fetch product schema", err)
      }
    }
    
    fetchSchema()
  }, [apiBase, selectedProduct])

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-spinner"></div>
        <h2>Loading GEO Assets...</h2>
      </div>
    )
  }

  if (fetchError) {
    return (
      <div className="error-screen">
        <h2>⚠️ Connection Error</h2>
        <p>{fetchError}</p>
        <button className="search-button" onClick={() => window.location.reload()}>Retry Connection</button>
      </div>
    )
  }

  return (
    <div className="geo-demo">
      <div className="geo-header">
        <h2>🚀 Generative Engine Optimization (GEO)</h2>
        <p className="geo-subtitle">
          Exporting semantic properties so external AI engines (Perplexity, ChatGPT) can "see" the graph.
        </p>
      </div>

      <div className="geo-content">
        <div className="product-selector">
          <label>Select Product to Preview Schema Injection:</label>
          <select 
            value={selectedProduct} 
            onChange={(e) => setSelectedProduct(e.target.value)}
            className="search-input select-input"
            style={{ backgroundColor: 'var(--bg-card)', color: 'white' }}
          >
            {products.length === 0 ? <option>No products loaded...</option> : null}
            {products.map(p => (
              <option key={p.id} value={p.id} style={{ backgroundColor: 'var(--bg-secondary)', color: 'white' }}>{p.title}</option>
            ))}
          </select>
        </div>

        <div className="schema-comparison">
          <div className="schema-column baseline-schema">
            <div className="schema-column-header">
              <h3>Shopify Default Schema</h3>
              <span className="method-badge flat-badge">Basic</span>
            </div>
            <div className="schema-explanation">
              What standard Shopify platforms output via JSON-LD. Minimal context.
            </div>
            <pre className="code-block">
              <code>{geoData?.shopify_baseline || 'Loading...'}</code>
            </pre>
          </div>

          <div className="schema-column enhanced-schema">
            <div className="schema-column-header">
              <h3>Veracity Layer Schema</h3>
              <span className="method-badge graph-badge">Graph Enriched</span>
            </div>
            <div className="schema-explanation">
              Automatically injected metadata featuring connected properties and relationships.
            </div>
            <pre className="code-block enhanced-code">
              <code>{geoData?.veracity_enhanced || 'Loading...'}</code>
            </pre>
          </div>
        </div>

        <div className="llms-txt-section">
          <div className="schema-column-header">
            <h3>Domain Root /llms.txt</h3>
            <span className="method-badge category-badge">Global Crawler File</span>
          </div>
          <div className="schema-explanation">
            A dynamic markdown file hosted at the root domain that instructs AI agents precisely how to navigate the catalog functionally.
          </div>
          <pre className="code-block markdown-block">
            <code>{llmsTxt || 'Loading...'}</code>
          </pre>
        </div>
      </div>
    </div>
  )
}
