import { useState, useEffect } from 'react';
import Navigation from './components/Navigation';
import HomePage from './components/HomePage';
import FacultyFinder from './components/FacultyFinder';
import AboutPage from './components/AboutPage';
import ContactPage from './components/ContactPage';
import ProfessorDetailPage from './components/ProfessorDetailPage';
import Footer from './components/Footer';
import { PageType } from './types';

const API_BASE = 'https://finalresearchhelper-production.up.railway.app';

function App() {
  const [currentPage, setCurrentPage] = useState<PageType>('home');
  const [selectedProfessorId, setSelectedProfessorId] = useState<string | null>(null);

  // Count this browser as a unique visit (cookie prevents double-counting)
  useEffect(() => {
    fetch(`${API_BASE}/metrics/visit`, {
      method: 'POST',
      credentials: 'include', // important so the cookie is set/read
      headers: { 'Content-Type': 'application/json' },
    }).catch(() => {});
  }, []);

  const handleProfessorSelect = (professorId: string) => {
    setSelectedProfessorId(professorId);
    setCurrentPage('professor-detail');
  };

  return (
    <div className="min-h-screen">
      <Navigation currentPage={currentPage} setCurrentPage={setCurrentPage} />
      
      <main className="animate-fade-in">
        {currentPage === 'home' && <HomePage setCurrentPage={setCurrentPage} />}
        {currentPage === 'finder' && <FacultyFinder onProfessorSelect={handleProfessorSelect} />}
        {currentPage === 'about' && <AboutPage />}
        {currentPage === 'contact' && <ContactPage />}
        {currentPage === 'professor-detail' && selectedProfessorId && (
          <ProfessorDetailPage 
            professorId={selectedProfessorId} 
            onBack={() => setCurrentPage('finder')} 
          />
        )}
      </main>
      
      <Footer setCurrentPage={setCurrentPage} />
    </div>
  );
}

export default App;
