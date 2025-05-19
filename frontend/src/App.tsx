import React from 'react';
import './App.css';
import ChatInterface from './components/ChatInterface';

function App() {
  return (
    <div className="App">
      <header className="card" style={{
        padding: '1.25rem',
        margin: '1.5rem 1rem',
        backgroundColor: 'white'
      }}>
        <h1 style={{
          margin: 0,
          fontSize: '24px',
          color: 'var(--text-primary)',
          textAlign: 'center'
        }}>
          Assit
        </h1>
      </header>
      <main style={{ padding: '0 1rem' }}>
        <ChatInterface />
      </main>
    </div>
  );
}

export default App;
