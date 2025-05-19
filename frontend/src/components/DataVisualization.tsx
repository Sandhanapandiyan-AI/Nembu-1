import React, { useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Pie, Bar, Line } from 'react-chartjs-2';
import './DataVisualization.css';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

interface DataVisualizationProps {
  data: {
    columns: string[];
    rows: any[];
  };
  initialChartType?: 'pie' | 'bar' | 'line' | 'table';
  showTableByDefault?: boolean;
  formattedHeaders?: string[];
}

const DataVisualization: React.FC<DataVisualizationProps> = ({
  data,
  initialChartType = 'bar',
  showTableByDefault = false,
  formattedHeaders
}) => {
  // If there's only one column, force table view
  const [chartType, setChartType] = useState<'pie' | 'bar' | 'line' | 'table' | null>(
    data.columns.length <= 1 ? 'table' : initialChartType
  );
  const [labelColumn, setLabelColumn] = useState<string | null>(null);
  const [valueColumn, setValueColumn] = useState<string | null>(null);
  const [isFormatted, setIsFormatted] = useState<boolean>(true);

  // Map of original column names to formatted display names
  const columnDisplayNames = React.useMemo(() => {
    if (!formattedHeaders || formattedHeaders.length !== data.columns.length) {
      return {};
    }

    const displayMap: Record<string, string> = {};
    data.columns.forEach((col, index) => {
      displayMap[col] = formattedHeaders[index];
    });

    return displayMap;
  }, [data.columns, formattedHeaders]);

  // Find numeric columns for values
  const numericColumns = data.columns.filter(col => {
    if (data.rows.length === 0) return false;
    const value = data.rows[0][col];
    return typeof value === 'number' || !isNaN(Number(value));
  });

  // Find string/categorical columns for labels
  const categoricalColumns = data.columns.filter(col => {
    if (data.rows.length === 0) return false;
    const value = data.rows[0][col];
    return typeof value === 'string' || value instanceof String;
  });

  // We check data.columns.length > 1 directly in the render function

  // All columns for complete selection options
  const allColumns = data.columns;

  // Auto-select appropriate columns on mount
  React.useEffect(() => {
    // For bar chart, specifically select department_name and department_identifier
    if (chartType === 'bar') {
      // Find department_name column for label
      const departmentNameColumn = data.columns.find(col =>
        col.toLowerCase().includes('department_name')
      );

      // Find department_identifier column for value
      const departmentIdColumn = data.columns.find(col =>
        col.toLowerCase().includes('department_identifier')
      );

      // Set the columns if found
      if (departmentNameColumn) {
        setLabelColumn(departmentNameColumn);
      }

      if (departmentIdColumn) {
        setValueColumn(departmentIdColumn);
      }
    }
    // For other chart types, use the original auto-selection logic
    else {
      // Auto-select categorical column for labels
      if (!labelColumn && categoricalColumns.length > 0) {
        // Prefer department_name or name columns if available
        const preferredLabelColumns = ['department_name', 'name', 'employee_first_name', 'employee_last_name'];
        const preferredColumn = categoricalColumns.find(col =>
          preferredLabelColumns.some(preferred => col.toLowerCase().includes(preferred.toLowerCase()))
        );

        setLabelColumn(preferredColumn || categoricalColumns[0]);
      }

      // Auto-select numeric column for values
      if (!valueColumn && numericColumns.length > 0) {
        // Prefer salary or amount columns if available
        const preferredValueColumns = ['salary', 'amount', 'price', 'cost', 'revenue', 'count'];
        const preferredColumn = numericColumns.find(col =>
          preferredValueColumns.some(preferred => col.toLowerCase().includes(preferred.toLowerCase()))
        );

        setValueColumn(preferredColumn || numericColumns[0]);
      }
    }
  }, [chartType, data.columns, categoricalColumns, numericColumns, labelColumn, valueColumn]);

  const handleVisualize = (type: 'pie' | 'bar' | 'line' | 'table') => {
    setChartType(type);

    // Reset column selections when changing chart type
    if (type === 'bar') {
      // For bar chart, find department columns
      const departmentNameColumn = data.columns.find(col =>
        col.toLowerCase().includes('department_name')
      );

      const departmentIdColumn = data.columns.find(col =>
        col.toLowerCase().includes('department_identifier')
      );

      // Set the columns if found
      if (departmentNameColumn) {
        setLabelColumn(departmentNameColumn);
      }

      if (departmentIdColumn) {
        setValueColumn(departmentIdColumn);
      }
    } else if (type !== 'table') {
      // For other chart types (except table), reset to default selections
      // Auto-select categorical column for labels
      if (categoricalColumns.length > 0) {
        const preferredLabelColumns = ['department_name', 'name', 'employee_first_name', 'employee_last_name'];
        const preferredColumn = categoricalColumns.find(col =>
          preferredLabelColumns.some(preferred => col.toLowerCase().includes(preferred.toLowerCase()))
        );

        setLabelColumn(preferredColumn || categoricalColumns[0]);
      }

      // Auto-select numeric column for values
      if (numericColumns.length > 0) {
        const preferredValueColumns = ['salary', 'amount', 'price', 'cost', 'revenue', 'count'];
        const preferredColumn = numericColumns.find(col =>
          preferredValueColumns.some(preferred => col.toLowerCase().includes(preferred.toLowerCase()))
        );

        setValueColumn(preferredColumn || numericColumns[0]);
      }
    }
  };

  const formatValue = (value: number): string => {
    if (isFormatted) {
      // Check if it's likely a currency value
      if (valueColumn?.toLowerCase().includes('salary') ||
          valueColumn?.toLowerCase().includes('price') ||
          valueColumn?.toLowerCase().includes('cost') ||
          valueColumn?.toLowerCase().includes('revenue')) {
        return `₹${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
      }

      // Format large numbers with commas
      if (value >= 1000) {
        return value.toLocaleString();
      }

      // Format percentages
      if (valueColumn?.toLowerCase().includes('percent') || valueColumn?.toLowerCase().includes('rate')) {
        return `${value.toFixed(2)}%`;
      }
    }

    return String(value);
  };

  const prepareChartData = () => {
    if (!labelColumn || !valueColumn || !data.rows.length) {
      return {
        labels: [],
        datasets: [{
          data: [],
          backgroundColor: [],
        }]
      };
    }

    // Group data by label column and sum values
    const groupedData: Record<string, number> = {};

    data.rows.forEach(row => {
      const label = String(row[labelColumn]);
      const value = Number(row[valueColumn]);

      if (!isNaN(value)) {
        if (groupedData[label]) {
          groupedData[label] += value;
        } else {
          groupedData[label] = value;
        }
      }
    });

    // Generate colors
    const generateColors = (count: number) => {
      const colors = [];
      for (let i = 0; i < count; i++) {
        const hue = (i * 137) % 360; // Use golden angle for nice distribution
        colors.push(`hsl(${hue}, 70%, 60%)`);
      }
      return colors;
    };

    const labels = Object.keys(groupedData);
    const values = Object.values(groupedData);
    const colors = generateColors(labels.length);

    // Get display name for the value column
    const valueDisplayName = columnDisplayNames[valueColumn] || valueColumn;

    return {
      labels,
      datasets: [{
        label: valueDisplayName, // Use formatted column name
        data: values,
        backgroundColor: colors,
        borderColor: colors.map(color => color.replace('60%', '50%')),
        borderWidth: 1,
      }]
    };
  };

  const chartData = prepareChartData();

  const renderChart = () => {
    // For table view, we don't need label and value columns
    if (chartType === 'table') {
      // Continue to table rendering
    }
    // For chart views, we need label and value columns
    else if (!chartType || !labelColumn || !valueColumn) {
      return null;
    }

    // For table view, render a complete data table with all columns
    if (chartType === 'table') {
      return (
        <div className="data-table-container">
          <table className="data-table">
            <thead>
              <tr>
                {data.columns.map((col, index) => (
                  <th key={index}>
                    {columnDisplayNames[col] || col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.rows.map((row, rowIndex) => (
                <tr key={rowIndex}>
                  {data.columns.map((col, colIndex) => {
                    const value = row[col];
                    let displayValue: React.ReactNode;

                    // Format values appropriately
                    if (typeof value === 'number' && isFormatted) {
                      if (col.toLowerCase().includes('salary') ||
                          col.toLowerCase().includes('price') ||
                          col.toLowerCase().includes('cost')) {
                        displayValue = `₹${value.toLocaleString()}`;
                      } else {
                        displayValue = value.toLocaleString();
                      }
                    } else if (value instanceof Date) {
                      displayValue = value.toLocaleDateString();
                    } else if (value === null || value === undefined) {
                      displayValue = '-';
                    } else {
                      displayValue = String(value);
                    }

                    return <td key={colIndex}>{displayValue}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    // For chart views, use Chart.js
    const options = {
      responsive: true,
      plugins: {
        legend: {
          position: 'top' as const,
        },
        title: {
          display: true,
          text: `${valueColumn} by ${labelColumn}`,
        },
        tooltip: {
          callbacks: {
            label: function(context: any) {
              // Different handling based on chart type
              if (chartType === 'pie') {
                // For pie charts, context.parsed is the raw value
                const value = context.parsed;
                const label = context.label || '';
                const formattedValue = isFormatted ? formatValue(value) : value;
                return `${label}: ${formattedValue}`;
              } else if (chartType === 'bar' || chartType === 'line') {
                // For bar and line charts
                const label = context.dataset.label || '';
                let value;

                if (chartType === 'bar') {
                  // For bar charts, the y value contains the data
                  value = context.parsed.y;
                } else {
                  // For line charts, depending on orientation
                  value = context.parsed.y;
                }

                const formattedValue = isFormatted ? formatValue(value) : value;
                return `${label}: ${formattedValue}`;
              }

              // Fallback for any other chart type
              return context.formattedValue;
            },
            // Add title callback to show the x-axis label (usually the category)
            title: function(context: any[]) {
              // Return the label (x-value) for the first item in the tooltip
              return context.length > 0 ? context[0].label : '';
            }
          }
        }
      },
      scales: chartType !== 'pie' ? {
        y: {
          ticks: {
            callback: function(value: any) {
              return isFormatted ? formatValue(value) : value;
            }
          }
        }
      } : undefined
    };

    // Create specific options for pie charts
    const pieOptions = {
      ...options,
      plugins: {
        ...options.plugins,
        tooltip: {
          ...options.plugins.tooltip,
          callbacks: {
            label: function(context: any) {
              const label = context.label || '';
              const value = context.raw;
              const formattedValue = isFormatted ? formatValue(value) : value;

              // Calculate percentage
              const total = context.dataset.data.reduce((sum: number, val: number) => sum + val, 0);
              const percentage = ((value / total) * 100).toFixed(1);

              return `${label}: ${formattedValue} (${percentage}%)`;
            }
          }
        }
      }
    };

    // Create specific options for bar charts
    const barOptions = {
      ...options,
      plugins: {
        ...options.plugins,
        tooltip: {
          ...options.plugins.tooltip,
          callbacks: {
            label: function(context: any) {
              const label = valueColumn ? (columnDisplayNames[valueColumn] || valueColumn) : '';
              const value = context.parsed.y;
              const formattedValue = isFormatted ? formatValue(value) : value;
              return `${label}: ${formattedValue}`;
            },
            title: function(context: any[]) {
              if (context.length > 0) {
                const item = context[0];
                const label = item.label || '';
                return label;
              }
              return '';
            }
          }
        }
      }
    };

    // Create specific options for line charts
    const lineOptions = {
      ...options,
      plugins: {
        ...options.plugins,
        tooltip: {
          ...options.plugins.tooltip,
          callbacks: {
            label: function(context: any) {
              const label = valueColumn ? (columnDisplayNames[valueColumn] || valueColumn) : '';
              const value = context.parsed.y;
              const formattedValue = isFormatted ? formatValue(value) : value;
              return `${label}: ${formattedValue}`;
            },
            title: function(context: any[]) {
              if (context.length > 0) {
                const item = context[0];
                const label = item.label || '';
                return label;
              }
              return '';
            }
          }
        }
      }
    };

    switch (chartType) {
      case 'pie':
        return <Pie data={chartData} options={pieOptions} />;
      case 'bar':
        return <Bar data={chartData} options={barOptions} />;
      case 'line':
        return <Line data={chartData} options={lineOptions} />;
      default:
        return null;
    }
  };

  return (
    <div className="data-visualization">
      <div className="visualization-controls">
        <div style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '0.5rem',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1rem'
        }}>
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {/* Only show chart options if we have enough columns */}
            {data.columns.length > 1 && (
              <>
                <button
                  onClick={() => handleVisualize('bar')}
                  style={{
                    backgroundColor: chartType === 'bar' ? 'var(--accent-color)' : '#f0f0f0',
                    color: chartType === 'bar' ? 'white' : 'var(--text-primary)',
                  }}
                >
                  Bar Chart
                </button>
                <button
                  onClick={() => handleVisualize('pie')}
                  style={{
                    backgroundColor: chartType === 'pie' ? 'var(--accent-color)' : '#f0f0f0',
                    color: chartType === 'pie' ? 'white' : 'var(--text-primary)',
                  }}
                >
                  Pie Chart
                </button>
                <button
                  onClick={() => handleVisualize('line')}
                  style={{
                    backgroundColor: chartType === 'line' ? 'var(--accent-color)' : '#f0f0f0',
                    color: chartType === 'line' ? 'white' : 'var(--text-primary)',
                  }}
                >
                  Line Chart
                </button>
              </>
            )}
            <button
              onClick={() => handleVisualize('table')}
              style={{
                backgroundColor: chartType === 'table' ? 'var(--accent-color)' : '#f0f0f0',
                color: chartType === 'table' ? 'white' : 'var(--text-primary)',
              }}
            >
              Table
            </button>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
            {/* Only show controls for bar chart */}
            {chartType === 'bar' && (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <label>Label:</label>
                  <select
                    value={labelColumn || ''}
                    onChange={(e) => setLabelColumn(e.target.value)}
                    style={{ padding: '0.25rem' }}
                  >
                    <option value="">Select</option>
                    {/* Only show Department option for Label */}
                    {allColumns
                      .filter(col => col.toLowerCase().includes('department_name'))
                      .map(col => (
                        <option key={col} value={col}>{columnDisplayNames[col] || col}</option>
                      ))
                    }
                  </select>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <label>Value:</label>
                  <select
                    value={valueColumn || ''}
                    onChange={(e) => setValueColumn(e.target.value)}
                    style={{ padding: '0.25rem' }}
                  >
                    <option value="">Select</option>
                    {/* Only show Department ID option for Value */}
                    {allColumns
                      .filter(col => col.toLowerCase().includes('department_identifier'))
                      .map(col => (
                        <option key={col} value={col}>{columnDisplayNames[col] || col}</option>
                      ))
                    }
                  </select>
                </div>
              </>
            )}

            {/* For other chart types, show all options */}
            {chartType !== 'bar' && chartType !== 'table' && (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <label>Label:</label>
                  <select
                    value={labelColumn || ''}
                    onChange={(e) => setLabelColumn(e.target.value)}
                    style={{ padding: '0.25rem' }}
                  >
                    <option value="">Select</option>
                    {allColumns.map(col => (
                      <option key={col} value={col}>{columnDisplayNames[col] || col}</option>
                    ))}
                  </select>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <label>Value:</label>
                  <select
                    value={valueColumn || ''}
                    onChange={(e) => setValueColumn(e.target.value)}
                    style={{ padding: '0.25rem' }}
                  >
                    <option value="">Select</option>
                    {allColumns.map(col => (
                      <option key={col} value={col}>{columnDisplayNames[col] || col}</option>
                    ))}
                  </select>
                </div>
              </>
            )}

            {/* Only show Raw Values button for bar chart */}
            {chartType === 'bar' && (
              <button
                onClick={() => setIsFormatted(!isFormatted)}
                style={{
                  backgroundColor: isFormatted ? 'var(--accent-color)' : '#f0f0f0',
                  color: isFormatted ? 'white' : 'var(--text-primary)',
                }}
              >
                {isFormatted ? 'Raw Values' : 'Format Values'}
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="chart-container">
        {renderChart()}
      </div>
    </div>
  );
};

export default DataVisualization;
