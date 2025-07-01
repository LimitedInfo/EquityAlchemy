import React, { useState, useEffect } from 'react';
import { getIncomeStatements, getFreeQueryStatus, forecastFinancialData } from '../services/api';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@clerk/clerk-react';

function FinancialData() {
  const [ticker, setTicker] = useState('');
  const [formType, setFormType] = useState('10-K');
  const [financialData, setFinancialData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [freeQueryStatus, setFreeQueryStatus] = useState(null);
  const [showLoginPrompt, setShowLoginPrompt] = useState(false);
  const [forecastData, setForecastData] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(false);
  const [forecastError, setForecastError] = useState('');
  const [showForecast, setShowForecast] = useState(false);
  const navigate = useNavigate();
  const { isSignedIn } = useAuth();

  useEffect(() => {
    const checkFreeQueryStatus = async () => {
      if (!isSignedIn) {
        try {
          const response = await getFreeQueryStatus();
          setFreeQueryStatus(response.data);
        } catch (err) {
          console.error('Failed to get free query status:', err);
        }
      }
    };

    checkFreeQueryStatus();
  }, [isSignedIn]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setShowLoginPrompt(false);

    try {
      const response = await getIncomeStatements(ticker, formType || null);
      setFinancialData(response.data);

      if (!isSignedIn && response.headers['x-free-query-used'] === 'true') {
        setShowLoginPrompt(true);
        setFreeQueryStatus(prev => ({
          ...prev,
          free_queries_used: 1,
          free_queries_remaining: 0,
          has_free_queries: false
        }));
      }
    } catch (err) {
      console.error('Financial data fetch error:', err);

      if (err.response && err.response.status === 401) {
        if (err.response.headers['x-free-limit-exceeded'] === 'true') {
          setError('You have used your free query. Please sign in to access more financial data.');
          setShowLoginPrompt(true);
        } else if (!isSignedIn) {
          setError('Please sign in to access financial data.');
          setShowLoginPrompt(true);
        } else {
          setError('Authentication error. Please try again or contact support.');
        }
      } else {
        setError('Failed to fetch financial data');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLoginRedirect = () => {
    navigate('/login');
  };

  const handleForecast = async () => {
    if (!financialData || !ticker) {
      setForecastError('Please load financial data first');
      return;
    }

    setForecastLoading(true);
    setForecastError('');

    try {
      const response = await forecastFinancialData(ticker, formType || null, 10);
      setForecastData(response.data);
      setShowForecast(true);
    } catch (err) {
      console.error('Forecast error:', err);

      if (err.response && err.response.status === 401) {
        setForecastError('Please sign in to access forecasting features.');
        setShowLoginPrompt(true);
      } else if (err.response && err.response.status === 404) {
        setForecastError(`Financial data not found for forecasting. Error: ${err.response?.data?.detail || 'Unknown error'}`);
      } else {
        setForecastError(`Failed to generate forecast: ${err.response?.data?.detail || err.message || 'Unknown error'}`);
      }
    } finally {
      setForecastLoading(false);
    }
  };

  return (
    <div className="financial-container">
      <h2>Financial Data</h2>

      {!isSignedIn && freeQueryStatus && (
        <div className="free-query-info" style={{
          background: 'rgb(14, 13, 13)',
          border: '1px solid rgb(35, 184, 207)',
          padding: '10px',
          borderRadius: '5px',
          marginBottom: '20px',
          textAlign: 'center'
        }}>
          {freeQueryStatus.has_free_queries ? (
            <p><strong>Free Trial:</strong> You can make {freeQueryStatus.free_queries_remaining} free query before signing in.</p>
          ) : (
            <p><strong>Free Trial Used:</strong> Please sign in to continue accessing financial data.</p>
          )}
        </div>
      )}

      {showLoginPrompt && (
        <div className="login-prompt" style={{
          background: 'rgb(14, 13, 13)',
          border: '1px solid rgb(35, 184, 207)',
          padding: '15px',
          borderRadius: '5px',
          marginBottom: '20px',
          textAlign: 'center'
        }}>
          <p><strong>Enjoying the data?</strong> Sign in to get unlimited access to financial statements!</p>
          <button
            onClick={handleLoginRedirect}
            style={{
              background: '#007bff',
              color: 'white',
              border: 'none',
              padding: '8px 16px',
              borderRadius: '4px',
              cursor: 'pointer',
              marginTop: '10px'
            }}
          >
            Sign In Now
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Ticker Symbol:</label>
          <input
            type="text"
            value={ticker.toUpperCase()}
            onChange={(e) => setTicker(e.target.value)}
            required
          />
        </div>
        <div className="form-group">
          <label>Form Type:</label>
          <div className="radio-group" style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
            <label style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '5px', whiteSpace: 'nowrap' }}>
              <input
                type="radio"
                value="10-K"
                checked={formType === '10-K' || formType === ''}
                onChange={(e) => setFormType(e.target.value)}
              />
              10-K - Annual
            </label>
            <label style={{ fontSize: '12px', display: 'flex', alignItems: 'center', gap: '5px', color: '#888', whiteSpace: 'nowrap' }}>
              <input
                type="radio"
                value="10-Q"
                checked={formType === '10-Q'}
                onChange={(e) => setFormType(e.target.value)}
                disabled
              />
              10-Q - Coming Soon
            </label>
          </div>
        </div>
        <button
          type="submit"
          disabled={loading || (!isSignedIn && freeQueryStatus && !freeQueryStatus.has_free_queries)}
        >
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
                    <th key={period}>{period.split(':')[1] || period}</th>
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
                          ? metric.name.includes('EPS') || metric.name.includes('Earnings Per Share')
                            ? new Intl.NumberFormat('en-US', {
                                style: 'currency',
                                currency: 'USD',
                                minimumFractionDigits: 2,
                                maximumFractionDigits: 2
                              }).format(metric.values[period])
                            : metric.name.includes('Average Shares') || metric.name.includes('Shares')
                              ? new Intl.NumberFormat('en-US', {
                                  minimumFractionDigits: 0,
                                  maximumFractionDigits: 0
                                }).format(metric.values[period])
                              : new Intl.NumberFormat('en-US', {
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
{/*
          <div className="forecast-section" style={{ marginTop: '20px' }}>
            <button
              onClick={handleForecast}
              disabled={forecastLoading || !isSignedIn}
              style={{
                background: forecastLoading ? '#666' : '#28a745',
                color: 'white',
                border: 'none',
                padding: '10px 20px',
                borderRadius: '4px',
                cursor: forecastLoading || !isSignedIn ? 'not-allowed' : 'pointer',
                marginRight: '10px'
              }}
            >
              {forecastLoading ? 'Generating Forecast...' : '📈 Generate 10-Year Forecast'}
            </button>

            {showForecast && (
              <button
                onClick={() => setShowForecast(!showForecast)}
                style={{
                  background: '#6c757d',
                  color: 'white',
                  border: 'none',
                  padding: '10px 20px',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                {showForecast ? 'Hide Forecast' : 'Show Forecast'}
              </button>
            )}

            {!isSignedIn && (
              <p style={{ color: '#ffc107', fontSize: '12px', marginTop: '5px' }}>
                Sign in to access forecasting features
              </p>
            )}
          </div>

          {forecastError && (
            <div className="error" style={{ marginTop: '10px', color: '#dc3545' }}>
              {forecastError}
            </div>
          )}

          {forecastData && showForecast && (
            <div className="forecast-results" style={{ marginTop: '20px' }}>
              <h4>📊 10-Year Financial Forecast</h4>
              <p style={{ fontSize: '12px', color: '#888', marginBottom: '15px' }}>
                Forecast generated using Facebook Prophet. Historical data: {forecastData.metadata?.original_periods || 'N/A'} periods,
                Success rate: {forecastData.metadata?.success_rate?.toFixed(1) || 'N/A'}%
              </p>

              <div className="financial-table-container">
                <table className="financial-table">
                  <thead>
                    <tr>
                      <th>Metric</th>
                      {financialData.periods.map(period => (
                        <th key={period} style={{ background: '#f8f9fa' }}>
                          {period.split(':')[1] || period}
                        </th>
                      ))}
                      {forecastData.forecast_periods?.map(period => (
                        <th key={period} style={{ background: '#e3f2fd', color: '#1976d2' }}>
                          {period} 📈
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {financialData.metrics.map(metric => (
                      <tr key={metric.name}>
                        <td>{metric.name}</td>
                        {financialData.periods.map(period => (
                          <td key={`${metric.name}-${period}`} style={{ background: '#f8f9fa' }}>
                            {metric.values[period] !== undefined
                              ? metric.name.includes('EPS') || metric.name.includes('Earnings Per Share')
                                ? new Intl.NumberFormat('en-US', {
                                    style: 'currency',
                                    currency: 'USD',
                                    minimumFractionDigits: 2,
                                    maximumFractionDigits: 2
                                  }).format(metric.values[period])
                                : metric.name.includes('Average Shares') || metric.name.includes('Shares')
                                  ? new Intl.NumberFormat('en-US', {
                                      minimumFractionDigits: 0,
                                      maximumFractionDigits: 0
                                    }).format(metric.values[period])
                                  : new Intl.NumberFormat('en-US', {
                                      style: 'currency',
                                      currency: 'USD',
                                      minimumFractionDigits: 0,
                                      maximumFractionDigits: 0
                                    }).format(metric.values[period])
                              : '-'}
                          </td>
                        ))}
                        {forecastData.forecast_periods?.map(period => {
                          const forecastValue = forecastData.forecasted_data?.find(row => row.Metric === metric.name)?.[period];
                          return (
                            <td key={`${metric.name}-forecast-${period}`} style={{ background: '#e3f2fd', fontStyle: 'italic' }}>
                              {forecastValue !== undefined && forecastValue !== null
                                ? metric.name.includes('EPS') || metric.name.includes('Earnings Per Share')
                                  ? new Intl.NumberFormat('en-US', {
                                      style: 'currency',
                                      currency: 'USD',
                                      minimumFractionDigits: 2,
                                      maximumFractionDigits: 2
                                    }).format(forecastValue)
                                  : metric.name.includes('Average Shares') || metric.name.includes('Shares')
                                    ? new Intl.NumberFormat('en-US', {
                                        minimumFractionDigits: 0,
                                        maximumFractionDigits: 0
                                      }).format(forecastValue)
                                    : new Intl.NumberFormat('en-US', {
                                        style: 'currency',
                                        currency: 'USD',
                                        minimumFractionDigits: 0,
                                        maximumFractionDigits: 0
                                      }).format(forecastValue)
                                : '-'}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div style={{ marginTop: '10px', fontSize: '11px', color: '#666' }}>
                <p>💡 <strong>Forecast Legend:</strong></p>
                <p>• Blue columns (📈) represent AI-generated forecasts based on historical trends</p>
                <p>• Forecasts are estimates and should not be used as investment advice</p>
                <p>• Model: Facebook Prophet with {forecastData.metadata?.is_quarterly ? 'quarterly' : 'annual'} data detection</p>
              </div>
            </div>
          )} */}
        </div>
      )}
      <p><em>Units displayed in millions where applicable</em></p>
    </div>
  );
}

export default FinancialData;
