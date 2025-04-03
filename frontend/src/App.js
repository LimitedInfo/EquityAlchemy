import React, { useState } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Login from './components/Login';
import Profile from './components/Profile';
import FinancialData from './components/FinancialData';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  return (
    <Router>
      <div className="app">
        <Navbar isAuthenticated={isAuthenticated} setIsAuthenticated={setIsAuthenticated} />
        <main className="content">
          <Routes>
            <Route path="/login" element={
              <Login setIsAuthenticated={setIsAuthenticated} />
            } />
            <Route path="/profile" element={
              <Profile isAuthenticated={isAuthenticated} />
            } />
            <Route path="/financial" element={
              <FinancialData isAuthenticated={isAuthenticated} />
            } />
            <Route path="/" element={
              isAuthenticated ? <Navigate to="/profile" /> : <Navigate to="/login" />
            } />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
