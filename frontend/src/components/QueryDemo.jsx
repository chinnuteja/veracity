import { useState } from 'react'

export default function QueryDemo({ apiBase }) {
  const [query, setQuery] = useState('')
  const [flatResults, setFlatResults] = useState(null)
  const [graphResults, setGraphResults] = useState(null)
  const [loading, setLoading] = useState(false)

  const exampleQueries = [
    "I have digestion problems and want something with turmeric",
    "herbal tea for weight loss and metabolism",
    "something calming for before bed to help with sleep",
    "tea for skin health and glowing skin",
    "detox tea with antioxidants for daily routine",
    "gift set for someone who likes herbal wellness teas",
  ]

  const handleSearch = async (searchQuery) => {
    const q = searchQuery || query
    if (!q.trim()) return

    setLoading(true)
    setQuery(q)

    try {
      const [flatRes, graphRes] = await Promise.all([
        fetch(`${apiBase}/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, mode: 'flat' }),
        }).then(r => r.json()),
        fetch(`${apiBase}/query`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: q, mode: 'graph' }),
        }).then(r => r.json()),
      ])

      setFlatResults(flatRes)
      setGraphResults(graphRes)
    } catch (err) {
      console.error('Query failed:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="query-demo">
      {/* Search Bar */}
      <div className="query-input-section">
        <h2>⚡ Semantic Search Capabilities — Side by Side</h2>
        <p className="query-subtitle">
          Type a natural language question and observe how the Veracity Layer's graph-aware retrieval evaluates queries compared to standard lexical search.
        </p>

        <div className="search-bar">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="Ask a product question... e.g., 'tea for digestion with turmeric'"
            className="search-input"
          />
          <button
            onClick={() => handleSearch()}
            disabled={loading}
            className="search-button"
          >
            {loading ? '⏳' : '🔍'} Search
          </button>
        </div>

        <div className="example-queries">
          <span className="example-label">Try:</span>
          {exampleQueries.map((eq, i) => (
            <button
              key={i}
              className="example-chip"
              onClick={() => handleSearch(eq)}
            >
              {eq.length > 45 ? eq.substring(0, 45) + '…' : eq}
            </button>
          ))}
        </div>
      </div>

      {/* Results comparison */}
      {(flatResults || graphResults) && (
        <div className="results-comparison">
          {/* Standard Search Column */}
          <div className="result-column flat">
            <div className="column-header flat-header">
              <h3>Standard Text Retrieval</h3>
              <span className="method-badge flat-badge">Baseline Lexical Search</span>
            </div>
            {flatResults?.graph_path && (
              <div className="graph-path flat-path">
                <code>{flatResults.graph_path}</code>
              </div>
            )}
            <div className="result-list">
              {flatResults?.results?.length === 0 && (
                <div className="no-results">No keyword matches found.</div>
              )}
              {flatResults?.results?.map((r, i) => (
                <div key={i} className="result-card flat-card">
                  <div className="result-rank">#{i + 1}</div>
                  <div className="result-info">
                    <h4>{r.title}</h4>
                    <p className="result-price">₹{r.price}</p>
                    <p className="result-reasoning">{r.reasoning}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Enhanced Search Column */}
          <div className="result-column graph">
            <div className="column-header graph-header">
              <h3>Veracity Layer Engine</h3>
              <span className="method-badge graph-badge">Semantic Knowledge Graph</span>
            </div>
            {graphResults?.graph_path && (
              <div className="graph-path graph-path-highlight">
                <strong>Graph traversal:</strong>
                <code>{graphResults.graph_path}</code>
              </div>
            )}
            <div className="result-list">
              {graphResults?.results?.length === 0 && (
                <div className="no-results">No graph matches found.</div>
              )}
              {graphResults?.results?.map((r, i) => (
                <div key={i} className="result-card graph-card">
                  <div className="result-rank">#{i + 1}</div>
                  <div className="result-info">
                    <h4>{r.title}</h4>
                    <p className="result-price">₹{r.price}</p>
                    <p className="result-reasoning">{r.reasoning}</p>
                    {r.ingredients?.length > 0 && (
                      <div className="result-tags">
                        {r.ingredients.slice(0, 5).map((ing, j) => (
                          <span key={j} className="ingredient-tag">{ing}</span>
                        ))}
                      </div>
                    )}
                    {r.pairings?.length > 0 && (
                      <div className="result-pairings">
                        <span className="pairing-label">Pairs with:</span>
                        {r.pairings.map((p, j) => (
                          <span key={j} className="pairing-tag">{p}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
