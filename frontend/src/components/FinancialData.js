import React, { useState, useEffect } from 'react';
import { getIncomeStatements } from '../services/api';
import { useNavigate } from 'react-router-dom';

function FinancialData({ isAuthenticated }) {
  const [ticker, setTicker] = useState('');
  const [formType, setFormType] = useState('');
  const [financialData, setFinancialData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, navigate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await getIncomeStatements(ticker, formType || null);
      setFinancialData(response.data);
    } catch (err) {
      setError('Failed to fetch financial data');
      console.error('Financial data fetch error:', err);

      // If unauthorized, redirect to login
      if (err.response && err.response.status === 401) {
        navigate('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="financial-container">
      <h2>Financial Data</h2>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Ticker Symbol:</label>
          <input
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label>Form Type (optional):</label>
          <input
            type="text"
            value={formType}
            onChange={(e) => setFormType(e.target.value)}
            placeholder="e.g., 10-K, 10-Q"
          />
        </div>
        <button type="submit" disabled={loading}>
          {loading ? 'Loading...' : 'Get Data'}
        </button>
      </form>

      {error && <div className="error">{error}</div>}

      {financialData && (
        <div className="financial-results">
          <h3>{financialData.ticker} Financial Statements</h3>
          {financialData.form_type && <p>Form Type: {financialData.form_type}</p>}

          <div className="financial-table-container">
            <table className="financial-table">
              <thead>
                <tr>
                  <th>Metric</th>
                  {financialData.periods.map(period => (
                    <th key={period}>{period}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {financialData.metrics.map(metric => (
                  <tr key={metric.name}>
                    <td>{metric.name}</td>
                    {financialData.periods.map(period => (
                      <td key={`${metric.name}-${period}`}>
                        {metric.values[period] !== undefined
                          ? new Intl.NumberFormat('en-US', {
                              style: 'currency',
                              currency: 'USD',
                              minimumFractionDigits: 0,
                              maximumFractionDigits: 0
                            }).format(metric.values[period])
                          : '-'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

export default FinancialData;
