import React from 'react';
import { Link } from 'react-router-dom';
import { SignedIn, SignedOut, UserButton } from '@clerk/clerk-react';

function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-logo">
        <span style={{ display: 'flex', alignItems: 'center' }}>
          <img src="/favicon-32x32.png" alt="Equity Alchemy" style={{ marginRight: '8px' }} />
          <Link to="/" style={{
            color: '#7fffd4',
            textShadow: '0 0 2px rgb(27, 241, 55), 0 0 4px rgb(46, 231, 71)',
            fontWeight: 'bold'
          }}>Equity Alchemy</Link>
        </span>
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
            backgroundColor: 'rgb(49, 179, 66)',
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
