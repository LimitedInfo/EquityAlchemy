import React from 'react';
import { BrowserRouter as Router, Route, Routes, Navigate } from 'react-router-dom';
import Navbar from './components/Navbar';
import Profile from './components/Profile';
import FinancialData from './components/FinancialData';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app">
        <Navbar />
        <main className="content">
          <Routes>
            <Route path="/profile" element={
              <Profile />
            } />
            <Route path="/financial" element={
              <FinancialData />
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
