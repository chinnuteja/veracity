import React from 'react';

export default function EmptyState({ onAddStore }) {
  return (
    <div className="empty-state-container">
      <div className="empty-state-card">
        <div className="empty-state-icon">
          <svg width="64" height="64" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="url(#gradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M2 17L12 22L22 17" stroke="url(#gradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M2 12L12 17L22 12" stroke="url(#gradient)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            <defs>
              <linearGradient id="gradient" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
                <stop stopColor="#6366F1" />
                <stop offset="1" stopColor="#8B5CF6" />
              </linearGradient>
            </defs>
          </svg>
        </div>
        
        <h2>Welcome to Helio Veracity Layer</h2>
        <p>Your Semantic Knowledge Graph is currently empty. Connect a Shopify store to let our AI extract semantic attributes and build your dynamic graph.</p>
        
        <button className="action-btn primary empty-state-btn" onClick={onAddStore}>
          Connect a Shopify Store 🚀
        </button>
      </div>
      
      <div className="empty-state-bg-glow"></div>
    </div>
  );
}
