import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './components/AuthContext';
import Navigation from './components/Navigation';
import HomePage from './components/HomePage';
import FacultyFinder from './components/FacultyFinder';
import AboutPage from './components/AboutPage';
import ContactPage from './components/ContactPage';
import ProfessorDetailPage from './components/ProfessorDetailPage';
import LoginPage from './components/LoginPage';
import SignupPage from './components/SignupPage';
import UserDashboard from './components/UserDashboard';
import Footer from './components/Footer';

//const API_BASE = "http://localhost:5050";
const API_BASE = "https://finalresearchhelper-production.up.railway.app";

function App() {
  // Count this browser as a unique visit (cookie prevents double-counting)
  useEffect(() => {
    fetch(`${API_BASE}/metrics/visit`, {
      method: 'POST',
      credentials: 'include', // important so the cookie is set/read
      headers: { 'Content-Type': 'application/json' },
    }).catch(() => {});
  }, []);

  return (
    <AuthProvider>
      <Router>
        <div className="min-h-screen">
          <Navigation />

          <main className="animate-fade-in">
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/finder" element={<FacultyFinder />} />
              <Route path="/about" element={<AboutPage />} />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/professors/:id" element={<ProfessorDetailPage />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/signup" element={<SignupPage />} />
              <Route path="/dashboard" element={<UserDashboard />} />
            </Routes>
          </main>

          <Footer />
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;