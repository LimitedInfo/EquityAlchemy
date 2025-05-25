import React, { useState } from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Profile from './components/Profile';
import FinancialData from './components/FinancialData';
import Login from './components/Login';
import './App.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(true);

  return (
    <Router>
      <div className="app">
        <Navbar />
        <main className="content">
          <Routes>
            <Route path="/login" element={
              <Login setIsAuthenticated={setIsAuthenticated} />
            } />
            <Route path="/profile" element={
              <Profile />
            } />
            <Route path="/financial" element={
              <FinancialData isAuthenticated={isAuthenticated} />
            } />
            <Route path="/" element={
              <Navigate to="/profile" />
            } />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
