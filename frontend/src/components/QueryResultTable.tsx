import React from 'react';
import './QueryResultTable.css';

interface QueryResultTableProps {
  headers: string[];
  data: any[][];
  isLoading?: boolean;
  error?: string;
}

const QueryResultTable: React.FC<QueryResultTableProps> = ({
  headers,
  data,
  isLoading = false,
  error
}) => {
  if (error) {
    return <div className="error-message">{error}</div>;
  }

  if (isLoading) {
    return <div className="query-result-wrapper">Loading results...</div>;
  }

  if (!data || data.length === 0) {
    return (
      <div className="query-result-wrapper">
        <div className="no-results">No results found</div>
      </div>
    );
  }

  return (
    <div className="query-result-wrapper">
      <div className="query-result-header">
        {data.length} {data.length === 1 ? 'result' : 'results'} found
      </div>
      <table className="query-result-table">
        <thead>
          <tr>
            {headers.map((header, index) => (
              <th key={index}>{header}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default QueryResultTable;