import React, { useState, useEffect } from 'react';
import { getIncomeStatements, getFreeQueryStatus, getSecFilingsUrl, searchTickers, getPriceData } from '../services/api';
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
  const [secFilingsUrl, setSecFilingsUrl] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [priceData, setPriceData] = useState(null);
  const navigate = useNavigate();
  const { isSignedIn } = useAuth();

  useEffect(() => {
    const fetchSuggestions = async () => {
      if (ticker.length > 1) {
        try {
          const response = await searchTickers(ticker);
          setSuggestions(response.data);
          setShowSuggestions(true);
          setHighlightedIndex(-1); // Reset highlighted index when new suggestions load
        } catch (err) {
          console.error('Failed to fetch ticker suggestions:', err);
        }
      } else {
        setSuggestions([]);
        setShowSuggestions(false);
        setHighlightedIndex(-1);
      }
    };

    const debounceFetch = setTimeout(() => {
      fetchSuggestions();
    }, 300);

    return () => clearTimeout(debounceFetch);
  }, [ticker]);

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

  const handleKeyDown = (e) => {
    if (!showSuggestions || suggestions.length === 0) return;

    switch (e.key) {
      case 'Tab':
        e.preventDefault(); // Prevent normal tab behavior
        setHighlightedIndex(prevIndex => {
          const nextIndex = prevIndex < suggestions.length - 1 ? prevIndex + 1 : 0;
          return nextIndex;
        });
        break;
      case 'ArrowDown':
        e.preventDefault();
        setHighlightedIndex(prevIndex => {
          const nextIndex = prevIndex < suggestions.length - 1 ? prevIndex + 1 : 0;
          return nextIndex;
        });
        break;
      case 'ArrowUp':
        e.preventDefault();
        setHighlightedIndex(prevIndex => {
          const nextIndex = prevIndex > 0 ? prevIndex - 1 : suggestions.length - 1;
          return nextIndex;
        });
        break;
      case 'Enter':
        e.preventDefault(); // Prevent form submission
        if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
          const selectedCompany = suggestions[highlightedIndex];
          setTicker(selectedCompany.ticker);
          setSuggestions([]);
          setShowSuggestions(false);
          setHighlightedIndex(-1);
        } else if (suggestions.length > 0) {
          // If no item highlighted, select the first one
          const selectedCompany = suggestions[0];
          setTicker(selectedCompany.ticker);
          setSuggestions([]);
          setShowSuggestions(false);
          setHighlightedIndex(-1);
        }
        break;
      case 'Escape':
        setSuggestions([]);
        setShowSuggestions(false);
        setHighlightedIndex(-1);
        break;
      default:
        break;
    }
  };

  const isValidCompany = async (input) => {
    if (!input.trim()) return false;

    // First check current suggestions
    const isInCurrentSuggestions = suggestions.some(company =>
      company.ticker.toUpperCase() === input.toUpperCase() ||
      company.name.toUpperCase() === input.toUpperCase()
    );

    if (isInCurrentSuggestions) return true;

    // If not in current suggestions, search for exact match
    try {
      const response = await searchTickers(input);
      return response.data.some(company =>
        company.ticker.toUpperCase() === input.toUpperCase() ||
        company.name.toUpperCase() === input.toUpperCase()
      );
    } catch (err) {
      console.error('Error validating company:', err);
      return false;
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setShowLoginPrompt(false);

    // Validate the company exists in our database
    const isValid = await isValidCompany(ticker);
    if (!isValid) {
      setError('Please enter a valid company name or ticker symbol. Use the suggestions dropdown to find valid companies.');
      setLoading(false);
      return;
    }

    try {
      const financialResponse = await getIncomeStatements(ticker, formType || null);
      setFinancialData(financialResponse.data);

      // Fetch price data separately without blocking
      getPriceData(ticker, 30)
        .then(priceResponse => setPriceData(priceResponse.data))
        .catch(err => console.warn('Failed to fetch price data:', err));

      // Fetch SEC URL separately without blocking
      getSecFilingsUrl(ticker, formType || '10-K')
        .then(secResponse => setSecFilingsUrl(secResponse.data.sec_filings_url))
        .catch(err => console.warn('Failed to fetch SEC filings URL:', err));

      if (!isSignedIn && financialResponse.headers['x-free-query-used'] === 'true') {
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


  const handleExportCsv = () => {
    if (!financialData) {
      setError('No financial data to export');
      return;
    }

    try {
      // Create CSV content with the same formatting as the table
      let csvContent = 'Metric';

      // Add headers (periods)
      financialData.periods.forEach(period => {
        csvContent += `,${period.split(':')[1] || period}`;
      });
      csvContent += '\n';

      // Add data rows with formatting
      financialData.metrics.forEach(metric => {
        csvContent += `"${metric.name}"`;

        financialData.periods.forEach(period => {
          const value = metric.values[period];
          let formattedValue = '-';

          if (value !== undefined && value !== null) {
            if (metric.name.includes('EPS') || metric.name.includes('Earnings Per Share')) {
              // EPS formatting (2 decimal places)
              formattedValue = new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
              }).format(value);
            } else if (metric.name.includes('Average Shares') || metric.name.includes('Shares')) {
              // Shares formatting (no decimal places)
              formattedValue = new Intl.NumberFormat('en-US', {
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
              }).format(value);
            } else {
              // Regular currency formatting (no decimal places)
              formattedValue = new Intl.NumberFormat('en-US', {
                style: 'currency',
                currency: 'USD',
                minimumFractionDigits: 0,
                maximumFractionDigits: 0
              }).format(value);
            }
          }

          csvContent += `,"${formattedValue}"`;
        });
        csvContent += '\n';
      });

      // Create and trigger download
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${ticker}_${formType || '10-K'}_financial_data.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

    } catch (error) {
      console.error('Error exporting CSV:', error);
      setError(`Error exporting CSV: ${error.message}`);
    }
  };

  return (
    <div className="financial-container">
      <h2>Financial Data</h2>

      {!isSignedIn && freeQueryStatus && (
        <div className="free-query-info" style={{
          background: 'rgb(14, 13, 13)',
          border: '1px solid rgb(128, 223, 141)',
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
          border: '1px solid rgb(128, 223, 141)',
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
          <label>Company Name or Ticker Symbol:</label>
          <div className="ticker-input-container" style={{ position: 'relative' }}>
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              onKeyDown={handleKeyDown}
              onFocus={() => ticker.length > 1 && setShowSuggestions(true)}
              onBlur={() => setTimeout(() => setShowSuggestions(false), 100)}
              placeholder="e.g., AAPL or Apple Inc"
              required
            />
            {showSuggestions && suggestions.length > 0 && (
              <ul className="suggestions-list" style={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                background: '#333',
                border: '1px solid #555',
                borderRadius: '4px',
                listStyle: 'none',
                padding: '5px 0',
                margin: 0,
                zIndex: 1000,
              }}>
                {suggestions.map((suggestion, index) => (
                  <li
                    key={index}
                    onClick={() => {
                      setTicker(suggestion.ticker);
                      setSuggestions([]);
                      setShowSuggestions(false);
                      setHighlightedIndex(-1);
                    }}
                    onMouseEnter={() => setHighlightedIndex(index)}
                    style={{
                      padding: '8px 12px',
                      cursor: 'pointer',
                      borderBottom: index < suggestions.length - 1 ? '1px solid #444' : 'none',
                      backgroundColor: index === highlightedIndex ? '#4a5568' : 'transparent',
                      transition: 'background-color 0.1s ease',
                    }}
                    onMouseDown={(e) => e.preventDefault()}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontWeight: 'bold', color: index === highlightedIndex ? '#ffffff' : '#80df8d' }}>{suggestion.ticker}</span>
                      <span style={{ fontSize: '12px', color: index === highlightedIndex ? '#e2e8f0' : '#ccc', marginLeft: '10px' }}>{suggestion.name}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <div style={{ fontSize: '11px', color: '#888', marginTop: '5px' }}>
              💡 Use Tab/Arrow keys to navigate, Enter to select, Escape to close
            </div>
          </div>
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

      {priceData && priceData.prices && priceData.prices.length > 0 && (
        <div className="price-chart-container" style={{ marginBottom: '30px' }}>
          <h3>{ticker} Stock Price - Last 30 Days</h3>
          <div style={{ background: 'rgb(14, 13, 13)', border: '1px solid #555', borderRadius: '5px', padding: '20px' }}>
                          {(() => {
                const prices = priceData.prices.filter(p => p > 0);
                if (prices.length === 0) return <p style={{ color: '#ccc', textAlign: 'center' }}>No price data available</p>;

                const maxPrice = Math.max(...prices);
                const minPrice = Math.min(...prices);
                const priceRange = maxPrice - minPrice || 1;
                const chartHeight = 200;
                const chartWidth = 600;
                const padding = 40;

                return (
                  <>
                    <svg viewBox={`0 0 ${chartWidth + 2 * padding} ${chartHeight + 2 * padding}`} style={{ width: '100%', height: 'auto' }}>
                      <line x1={padding} y1={padding} x2={padding} y2={chartHeight + padding} stroke="#888" strokeWidth="1" />
                      <line x1={padding} y1={chartHeight + padding} x2={chartWidth + padding} y2={chartHeight + padding} stroke="#888" strokeWidth="1" />

                      <text x={padding - 35} y={padding + 5} fill="#ccc" fontSize="12">${maxPrice.toFixed(2)}</text>
                      <text x={padding - 35} y={chartHeight + padding + 5} fill="#ccc" fontSize="12">${minPrice.toFixed(2)}</text>

                      <polyline
                        fill="none"
                        stroke="rgb(128, 223, 141)"
                        strokeWidth="2"
                        points={prices.map((price, i) => {
                          const x = padding + (i / (prices.length - 1)) * chartWidth;
                          const y = padding + chartHeight - ((price - minPrice) / priceRange) * chartHeight;
                          return `${x},${y}`;
                        }).join(' ')}
                      />

                      {prices.map((price, i) => {
                        const x = padding + (i / (prices.length - 1)) * chartWidth;
                        const y = padding + chartHeight - ((price - minPrice) / priceRange) * chartHeight;
                        return (
                          <circle key={i} cx={x} cy={y} r="3" fill="rgb(128, 223, 141)"
                            title={`$${price.toFixed(2)}`}>
                            <title>${price.toFixed(2)}</title>
                          </circle>
                        );
                      })}
                    </svg>
                    <div style={{ marginTop: '10px', display: 'flex', justifyContent: 'space-between', fontSize: '14px', color: '#ccc' }}>
                      <span>Current: ${prices[prices.length - 1].toFixed(2)}</span>
                      {priceData.price_changes && priceData.price_changes.length > 0 && (
                        <span style={{ color: priceData.price_changes[priceData.price_changes.length - 1] >= 0 ? 'rgb(128, 223, 141)' : '#ff6b6b' }}>
                          {priceData.price_changes[priceData.price_changes.length - 1] >= 0 ? '+' : ''}
                          {priceData.price_changes[priceData.price_changes.length - 1]?.toFixed(2)}%
                        </span>
                      )}
                    </div>
                  </>
                );
              })()}
          </div>
        </div>
      )}

      {financialData && (
        <div className="financial-results">
          <h3>{financialData.ticker} Financial Statements</h3>
          {financialData.form_type && <p>Form Type: {financialData.form_type}</p>}

          <div style={{ marginBottom: '15px' }}>
            <button
              onClick={handleExportCsv}
              style={{
                background: '#17a2b8',
                color: 'white',
                border: 'none',
                padding: '8px 16px',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '14px'
              }}
            >
              📄 Export to CSV
            </button>
          </div>

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
          <p><em>Units displayed in millions where applicable</em></p>
          {secFilingsUrl && (
            <div style={{ marginTop: '15px', padding: '10px', backgroundColor: '#3A3F4B', borderRadius: '5px', textAlign: 'center', border: '1px solidrgb(75, 130, 185)' }}>
              <p style={{ margin: '0', color: '#F2F2F2' }}>
                Does something look off? Please check{' '}
                <a
                  href={secFilingsUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: '#C8C8C8', textDecoration: 'underline', fontWeight: '500' }}
                >
                  here
                </a>
                {' '}for the SEC filings.
              </p>
            </div>
          )}
        </div>
      )}

      <p style={{ marginTop: '15px', padding: '10px', borderRadius: '5px', textAlign: 'center', border: '1px solidrgb(75, 130, 185)' }}> <em> By using this service, you exempt us the provider of data, from any liability for any errors or omissions in the data.</em></p>
    </div>
  );
}

export default FinancialData;
