import React from 'react';
import ReactDOM from 'react-dom/client';
import { ClerkProvider } from '@clerk/clerk-react';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';

const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const PUBLISHABLE_KEY = isLocalhost ? process.env.REACT_APP_CLERK_PUBLISHABLE_KEY_LOCAL : process.env.REACT_APP_CLERK_PUBLISHABLE_KEY;

if (!PUBLISHABLE_KEY) {
  throw new Error("Missing Clerk Publishable Key");
}

console.log('Clerk key type:', PUBLISHABLE_KEY.startsWith('pk_live_') ? 'PRODUCTION' : 'DEVELOPMENT');
console.log('Clerk key prefix:', PUBLISHABLE_KEY.substring(0, 8) + '...');

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <ClerkProvider
      publishableKey={PUBLISHABLE_KEY}
      {...(!isLocalhost ? { proxyUrl: "https://clerk.equityalchemy.ai" } : {})}
      afterSignOutUrl="/financial"
      signInUrl="/login"
      signUpUrl="/signup"
    >
      <App />
    </ClerkProvider>
  </React.StrictMode>
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
