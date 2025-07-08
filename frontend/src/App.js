import React from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import { SignedIn, SignedOut } from '@clerk/clerk-react';
import Navbar from './components/Navbar';
import Profile from './components/Profile';
import FinancialData from './components/FinancialData';
import Login from './components/Login';
import SignUp from './components/SignUp';
import { useGoogleAnalytics } from './utils/googleAnalytics';
import './App.css';

function AppRoutes() {
  useGoogleAnalytics();

  return (
    <div className="app">
      <Navbar />
      <main className="content">
        <Routes>
          <Route path="/login/*" element={<Login />} />
          <Route path="/signup/*" element={<SignUp />} />
          <Route path="/profile" element={
            <SignedIn>
              <Profile />
            </SignedIn>
          } />
          <Route path="/financial" element={<FinancialData />} />
          <Route path="/" element={<Navigate to="/financial" />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppRoutes />
    </Router>
  );
}

export default App;
