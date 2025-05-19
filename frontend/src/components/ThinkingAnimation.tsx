import React from 'react';

const ThinkingAnimation: React.FC = () => {
  return (
    <div className="card" style={{
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      padding: '8px 16px',
      backgroundColor: 'white',
      boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)'
    }}>
      <span style={{
        fontSize: '14px',
        color: 'var(--text-secondary)'
      }}>
        Generating Responce
      </span>
      <div className="loading-dots">
        <span></span>
        <span></span>
        <span></span>
      </div>
    </div>
  );
};

export default ThinkingAnimation;
