import React, { useState, useEffect } from 'react';
import { getUserProfile } from '../services/api';
import { useNavigate } from 'react-router-dom';

function Profile({ isAuthenticated }) {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    const fetchProfile = async () => {
      try {
        const response = await getUserProfile();
        setProfile(response.data);
      } catch (err) {
        setError('Failed to load profile data');
        console.error('Profile fetch error:', err);

        // If unauthorized, redirect to login
        if (err.response && err.response.status === 401) {
          navigate('/login');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [isAuthenticated, navigate]);

  if (loading) return <div>Loading profile...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="profile-container">
      <h2>User Profile</h2>
      {profile && (
        <div className="profile-info">
          <p><strong>Username:</strong> {profile.username}</p>
        </div>
      )}
    </div>
  );
}

export default Profile;
