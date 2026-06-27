import React, { useState } from 'react';

export default function StoreIngestion({ apiBase, onIngestSuccess }) {
  const [storeUrl, setStoreUrl] = useState('');
  const [productLimit, setProductLimit] = useState(10);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successStats, setSuccessStats] = useState(null);
  
  const handleIngest = async (e) => {
    e.preventDefault();
    if (!storeUrl) {
      setError("Please enter a valid Shopify Store URL.");
      return;
    }
    
    setLoading(true);
    setError(null);
    setSuccessStats(null);
    
    try {
      // Pass use_cache=false to force a fresh fetch
      const url = new URL(`${apiBase}/ingest`);
      url.searchParams.append('store_url', storeUrl);
      url.searchParams.append('product_limit', productLimit);
      url.searchParams.append('use_cache', 'false');
      
      const response = await fetch(url.toString(), {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Error: ${response.statusText}`);
      }
      
      const data = await response.json();
      setSuccessStats(data);
      if (onIngestSuccess) {
        onIngestSuccess();
      }
    } catch (err) {
      console.error(err);
      setError("Failed to ingest store. Check console for details.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ingestion-container demo-panel">
      <div className="panel-header">
        <h2>📥 Ingest New Shopify Store</h2>
        <p>Enter any Shopify store URL to fetch its products, extract semantic attributes, and build a Knowledge Graph.</p>
      </div>
      
      <form onSubmit={handleIngest} className="ingestion-form">
        <div className="form-group">
          <label htmlFor="storeUrl">Shopify Store URL</label>
          <input
            type="url"
            id="storeUrl"
            placeholder="https://example.myshopify.com"
            value={storeUrl}
            onChange={(e) => setStoreUrl(e.target.value)}
            disabled={loading}
            required
            className="input-field"
          />
        </div>
        
        <div className="form-group">
          <label htmlFor="productLimit">Product Limit (max items to fetch)</label>
          <input
            type="number"
            id="productLimit"
            min="1"
            max="250"
            value={productLimit}
            onChange={(e) => setProductLimit(e.target.value)}
            disabled={loading}
            className="input-field"
          />
        </div>
        
        <button type="submit" className="action-btn primary" disabled={loading}>
          {loading ? 'Processing... (This may take a minute)' : 'Process Store'}
        </button>
      </form>
      
      {error && (
        <div className="error-message">
          ⚠️ {error}
        </div>
      )}
      
      {loading && (
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Running Ingestion Pipeline...</p>
          <ul className="loading-steps">
            <li>📦 Fetching products...</li>
            <li>🧹 Cleaning data...</li>
            <li>🧠 Extracting semantic attributes (Azure OpenAI)...</li>
            <li>🔨 Building Knowledge Graph...</li>
          </ul>
        </div>
      )}
      
      {successStats && (
        <div className="success-state">
          <h3>✅ Ingestion Complete!</h3>
          <div className="stats-grid">
            <div className="stat-card">
              <span className="stat-label">Products Fetched</span>
              <span className="stat-value">{successStats.products_fetched}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Attributes Extracted</span>
              <span className="stat-value">{successStats.attributes_extracted}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Nodes Created</span>
              <span className="stat-value">{successStats.graph_stats.total_nodes}</span>
            </div>
            <div className="stat-card">
              <span className="stat-label">Edges Created</span>
              <span className="stat-value">{successStats.graph_stats.total_edges}</span>
            </div>
          </div>
          <p className="success-hint">Switch to the "🔮 Knowledge Graph" tab to explore!</p>
        </div>
      )}
    </div>
  );
}
