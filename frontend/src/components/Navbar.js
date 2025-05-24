import React from 'react';
import { Link } from 'react-router-dom';

function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-logo">
        <Link to="/">Financial Data App</Link>
      </div>
      <ul className="navbar-links">
        <li><Link to="/profile">Profile</Link></li>
        <li><Link to="/financial">Financial Data</Link></li>
      </ul>
    </nav>
  );
}

export default Navbar;
