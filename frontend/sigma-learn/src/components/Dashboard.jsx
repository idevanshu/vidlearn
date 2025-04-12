// src/components/Dashboard.jsx
import React from 'react';
import { useNavigate } from 'react-router-dom';
import VideoDashboard from './VideoDashboard';

function Dashboard() {
  const navigate = useNavigate();

  const handleLogout = () => {
    // Implement actual logout logic (e.g., API call) if needed.
    // For now, we redirect to /login.
    navigate('/login');
  };

  return (
    <div className="container mx-auto p-6">
      <header className="flex justify-between items-center mb-8">
        <h1 className="text-4xl font-bold text-blue-600">Gyanai Dashboard</h1>
        <button
          onClick={handleLogout}
          className="bg-red-500 hover:bg-red-600 text-white font-semibold py-2 px-4 rounded"
        >
          Logout
        </button>
      </header>
      <VideoDashboard />
    </div>
  );
}

export default Dashboard;
