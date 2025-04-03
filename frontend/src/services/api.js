import axios from 'axios';

const API_URL = 'http://localhost:8000';

// Create axios instance with credentials
const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
});

// Authentication services
export const login = async (username, password) => {
  return api.post('/login', { username, password });
};

export const logout = async () => {
  return api.post('/logout');
};

export const getUserProfile = async () => {
  return api.get('/user/profile');
};

// Financial data services
export const getIncomeStatements = async (ticker, formType = null) => {
  let url = `/api/financial/income/${ticker}`;
  if (formType) {
    url += `?form_type=${formType}`;
  }
  return api.get(url);
};

export default api;
