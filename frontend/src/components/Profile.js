import React from 'react';
import { useUser } from '@clerk/clerk-react';

function Profile() {
  const { user, isLoaded } = useUser();

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!isLoaded) return <div>Loading profile...</div>;

  return (
    <div className="profile-container">
      <h2>User Profile</h2>
      {user && (
        <div className="profile-info" style={{
          background: 'gray',
          padding: '20px',
          borderRadius: '8px',
          border: '1px solid rgb(20, 92, 163)'
        }}>
          <div style={{ marginBottom: '15px' }}>
            <strong>Email:</strong>
            <span style={{ marginLeft: '10px', color: '#000000' }}>
              {user.primaryEmailAddress?.emailAddress || 'No email'}
            </span>
          </div>
          <div style={{ marginBottom: '15px' }}>
            <strong>Member Since:</strong>
            <span style={{ marginLeft: '10px', color: '#000000' }}>
              {formatDate(user.createdAt)}
            </span>
          </div>
          <div style={{ marginBottom: '15px' }}>
            <strong>Last Sign In:</strong>
            <span style={{ marginLeft: '10px', color: '#000000' }}>
              {formatDate(user.lastSignInAt)}
            </span>
          </div>
          <div style={{
            marginTop: '20px',
            padding: '15px',
            background: '#e7f3ff',
            borderRadius: '5px',
            border: '1px solid #bee5eb'
          }}>
            <h4 style={{ margin: '0 0 10px 0', color: '#0c5460' }}>Account Benefits</h4>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#495057' }}>
              <li>Unlimited financial data queries</li>
            </ul>
          </div>
        </div>
      )}
    </div>
  );
}

export default Profile;
