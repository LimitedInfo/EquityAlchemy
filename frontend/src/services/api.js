import axios from 'axios';

const API_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
});

// Add request interceptor to include Clerk session token
api.interceptors.request.use(async (config) => {
  // Check if we're in a browser environment and Clerk is available
  if (typeof window !== 'undefined' && window.Clerk) {
    try {
      const session = await window.Clerk.session;
      if (session) {
        const token = await session.getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
    } catch (error) {
      console.log('No active Clerk session:', error);
    }
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export const getFreeQueryStatus = async () => {
  return api.get('/api/free-query-status');
};

export const getIncomeStatements = async (ticker, formType = null) => {
  let url = `/api/financial/income/${ticker}`;
  if (formType) {
    url += `?form_type=${formType}`;
  }
  return api.get(url);
};

export const forecastFinancialData = async (ticker, formType = null, forecastYears = 10) => {
  let url = `/api/financial/forecast/${ticker}`;
  if (formType) {
    url += `?form_type=${formType}`;
  }

  const requestBody = {
    forecast_years: forecastYears
  };

  return api.post(url, requestBody);
};

export const getSecFilingsUrl = async (ticker, formType = "10-K") => {
  let url = `/api/financial/sec-filings-url/${ticker}`;
  if (formType) {
    url += `?form_type=${formType}`;
  }
  return api.get(url);
};

export const searchTickers = async (term) => {
  if (!term) {
    return { data: [] };
  }
  return api.get(`/api/tickers/search?term=${term}`);
};

export const getPriceData = (ticker, days = 30) => {
  return api.get(`/api/financial/prices/${ticker}?days=${days}`);
};

export const getValuation = (ticker, formType = "10-K") => {
  let url = `/api/financial/valuation/${ticker}`;
  if (formType) {
    url += `?form_type=${formType}`;
  }
  return api.get(url);
};

export default api;
