import React from 'react';
import { SignIn, SignedIn, SignedOut } from '@clerk/clerk-react';
import { Navigate } from 'react-router-dom';

function Login() {
  return (
    <div className="login-container" style={{
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      width: '100%',
      padding: '20px',
      boxSizing: 'border-box'
    }}>
      <SignedOut>
        <div style={{
          textAlign: 'center',
          maxWidth: '400px',
          width: '100%'
        }}>
          <h2 style={{
            marginBottom: '20px',
            fontSize: '28px',
            fontWeight: '600',
            color: 'white'
          }}>
            Sign In to Your Account
          </h2>
          <p style={{
            marginBottom: '40px',
            color: 'white',
            fontSize: '16px',
            lineHeight: '1.5'
          }}>
            Welcome back! Sign in to access your financial data dashboard.
          </p>
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            width: '100%'
          }}>
            <SignIn
              afterSignInUrl="/profile"
              signUpUrl="/signup"
              appearance={{
                elements: {
                  formButtonPrimary: {
                    fontSize: '14px',
                    textTransform: 'none',
                    backgroundColor: '#3b82f6',
                    '&:hover': {
                      backgroundColor: '#2563eb'
                    }
                  },
                  card: {
                    boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
                  }
                }
              }}
            />
          </div>
        </div>
      </SignedOut>
      <SignedIn>
        <Navigate to="/profile" replace />
      </SignedIn>
    </div>
  );
}

export default Login;
