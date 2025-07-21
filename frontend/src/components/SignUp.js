import React from 'react';
import { SignUp as ClerkSignUp, SignedIn, SignedOut } from '@clerk/clerk-react';
import { Navigate } from 'react-router-dom';

function SignUp() {
  return (
    <div className="signup-container" style={{
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
            Join Equity Alchemy
          </h2>
          <p style={{
            marginBottom: '40px',
            color: '#6b7280',
            fontSize: '16px',
            lineHeight: '1.5'
          }}>
            Create your account to get access to financial statements and premium features.
          </p>
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            width: '100%'
          }}>
            <ClerkSignUp
              afterSignUpUrl="/profile"
              signInUrl="/login"
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

export default SignUp;
