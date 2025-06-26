import React from 'react';
import { Link } from 'react-router-dom';
import { SignedIn, SignedOut, UserButton } from '@clerk/clerk-react';

function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-logo">
        <Link to="/">Financial Data App</Link>
      </div>
      <ul className="navbar-links">
        <li><Link to="/financial">Financial Data</Link></li>
        <SignedIn>
          <li><Link to="/profile">Profile</Link></li>
          <li><UserButton afterSignOutUrl="/financial" /></li>
        </SignedIn>
        <SignedOut>
          <li><Link to="/login">Sign In</Link></li>
          <li><Link to="/signup" style={{
            backgroundColor: '#3b82f6',
            color: 'white',
            padding: '8px 16px',
            borderRadius: '6px',
            textDecoration: 'none',
            fontSize: '14px'
          }}>Sign Up</Link></li>
        </SignedOut>
      </ul>
    </nav>
  );
}

export default Navbar;
