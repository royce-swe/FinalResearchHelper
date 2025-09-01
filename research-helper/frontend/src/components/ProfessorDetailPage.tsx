import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useLocation } from "react-router-dom";

interface Paper {
  title: string;
  year: number | string;
  journal: string;
  citations: number;
  abstract: string;
}

interface Professor {
  id: string;
  name: string;
  email: string;
  department: string;
  university: string;
  researchAreas: string[];
  biography: string;
  recentPapers: Paper[];
  profileImage?: string;
}

const ProfessorDetailPage: React.FC = () => {
  const { id: professorId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const passedProfessor = (location.state as { professor?: Professor })?.professor;

  const [professor, setProfessor] = useState<Professor | null>(passedProfessor || null);
  const [isLoading, setIsLoading] = useState(!passedProfessor); // if we already have professor, skip loading
  const queryParams = new URLSearchParams(location.search);
  const email = queryParams.get("email"); // "leavens@ucf.edu"

  const [studentName, setStudentName] = useState('');
  const [studentInterests, setStudentInterests] = useState('');
  const [studentSkills, setStudentSkills] = useState('');
  const [generatedEmail, setGeneratedEmail] = useState('');

  //const API_BASE = 'https://finalresearchhelper-production.up.railway.app';
  const API_BASE = "http://localhost:5050";

  const handleBack = () => navigate('/finder');

  // Check if ID looks like an OpenAlex ID (starts with "A" and numbers)
  const isValidProfessorId = professorId?.startsWith("A") && /^\w+$/.test(professorId);   
  const searchParams = new URLSearchParams(location.search);
  const emailFromQuery = searchParams.get("email") || "";

useEffect(() => {
  if (!professorId) {
    setIsLoading(false);
    return;
  }

  const controller = new AbortController();
  const fetchProfessorDetails = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(`${API_BASE}/professors/${encodeURIComponent(professorId)}`, {
        signal: controller.signal,
      });

      if (!response.ok) throw new Error("Failed to fetch professor details");

      const data = await response.json();
      data.researchAreas = Array.isArray(data.researchAreas) ? data.researchAreas : [];
      data.recentPapers = Array.isArray(data.recentPapers) ? data.recentPapers : [];

      // Merge email from query param if provided
      if (emailFromQuery) data.email = emailFromQuery;

      setProfessor(data);
    } catch (error) {
      if ((error as any)?.name !== "AbortError") {
        console.error(error);
        setProfessor(null);
      }
    } finally {
      setIsLoading(false);
    }
  };

  fetchProfessorDetails();
  return () => controller.abort();
}, [professorId, emailFromQuery]);

  const generateEmail = async () => {
    if (!professor) return;

    try {
      const response = await fetch(`${API_BASE}/draft-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          student_name: studentName || "Your Name",
          student_research_interests: studentInterests || "computer engineering and machine learning",
          student_skills: studentSkills || "Python, data analysis",
          professor: {
            name: professor.name,
            email: professor.email,
            researchAreas: professor.researchAreas || [],
            recentPapers: professor.recentPapers || []
          }
        })
      });

      const data = await response.json();
      setGeneratedEmail(response.ok && data.draft ? data.draft : "⚠️ Failed to generate draft email.");
    } catch (error) {
      console.error("Error generating email:", error);
      setGeneratedEmail("⚠️ Error connecting to AI email generator.");
    }
  };

  // Show spinner if URL looks invalid
  if (!isValidProfessorId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-24 w-24 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-lg text-gray-600">Professor information not available</p>
          <button type="button" onClick={handleBack} className="mt-4 btn-primary">
            Back to Faculty Finder
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-xl text-gray-600">Loading professor information...</p>
        </div>
      </div>
    );
  }

  if (!professor) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 via-white to-purple-50">
        <div className="text-center">
          <p className="text-xl text-gray-600">Professor not found</p>
          <button type="button" onClick={handleBack} className="mt-4 btn-primary">
            Back to Faculty Finder
          </button>
        </div>
      </div>
    );
  }

  const initials = professor.name
    ? professor.name.split(' ').filter(Boolean).map(n => n[0]).join('')
    : 'PF';

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 pt-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <button
          type="button"
          onClick={handleBack}
          className="mb-6 flex items-center text-blue-600 hover:text-blue-800 transition-colors"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
          Back to Faculty Finder
        </button>

        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <div className="glass rounded-3xl shadow-2xl p-8">
              <div className="flex items-start space-x-6">
                <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-3xl font-bold">
                  {initials}
                </div>
                <div className="flex-1">
                  <h1 className="text-4xl font-bold text-gray-900 mb-2">{professor.name}</h1>
                  <p className="text-xl text-gray-600 mb-2">{professor.department || 'Department info unavailable'}</p>
                  <p className="text-lg text-gray-500 mb-4">{professor.university}</p>
                  {professor.email && professor.email !== 'Not Available' && (
                    <a
                      href={`mailto:${professor.email}`}
                      className="inline-flex items-center text-blue-600 hover:text-blue-800 font-medium"
                    >
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                      </svg>
                      {professor.email}
                    </a>
                  )}
                </div>
              </div>
            </div>

            <div className="glass rounded-2xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Research Areas</h2>
              <div className="flex flex-wrap gap-3">
                {(professor.researchAreas || []).map((area, index) => (
                  <span key={`${area}-${index}`} className="px-4 py-2 bg-blue-100 text-blue-800 rounded-full font-medium">
                    {area}
                  </span>
                ))}
              </div>
            </div>

            <div className="glass rounded-2xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">Biography</h2>
              <p className="text-gray-700 leading-relaxed">{professor.biography || 'Biography not available.'}</p>
            </div>

            <div className="glass rounded-2xl shadow-lg p-6">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Recent Publications</h2>
              <div className="space-y-6">
                {(professor.recentPapers || []).map((paper, index) => (
                  <div key={`${paper.title}-${index}`} className="border-l-4 border-blue-500 pl-6 hover:bg-gray-50 rounded-r-lg p-4 transition-colors">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">{paper.title}</h3>
                    <div className="flex items-center space-x-4 text-sm text-gray-600 mb-3">
                      <span>{paper.journal}</span>
                      <span>•</span>
                      <span>{paper.year}</span>
                      <span>•</span>
                      <span>{paper.citations} citations</span>
                    </div>
                    <p className="text-gray-700 text-sm">{paper.abstract}</p>
                  </div>
                ))}
              </div>
            </div>
            <button
            onClick={async () => {
                const token = localStorage.getItem('research_helper_token');
                const response = await fetch(`${API_BASE}/user/connections`, {
                  method: 'POST',
                  headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                  },
                  body: JSON.stringify({
                    professorName: professor.name,
                    university: professor.university,
                    email: professor.email,
                    field: professor.department // using department as field
                  })
                });

                if (response.ok) {
                  alert('Professor saved to your dashboard!');
                } else {
                  alert('Failed to save professor. Make sure you are logged in.');
                }
              }}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg shadow-md transition-colors duration-200"
            >
              Save to Dashboard
          </button>
          </div>

          <div className="lg:col-span-1">
            <div className="glass rounded-2xl shadow-lg p-6 sticky top-24">
              <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
                ✉️ Personalized Email Generator
              </h2>

              <div className="space-y-3 mb-4">
                <input
                  type="text"
                  placeholder="Your Full Name"
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
                <input
                  type="text"
                  placeholder="Your Research Interests (e.g., AI, Robotics)"
                  value={studentInterests}
                  onChange={(e) => setStudentInterests(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
                <input
                  type="text"
                  placeholder="Your Skills (e.g., Python, Data Analysis)"
                  value={studentSkills}
                  onChange={(e) => setStudentSkills(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                />
              </div>

              <button
                type="button"
                onClick={generateEmail}
                className="w-full bg-green-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-green-700 transition-colors mb-4"
              >
                Generate Email Draft
              </button>

              {generatedEmail && (
                <div className="mt-4">
                  <h3 className="font-semibold text-gray-900 mb-2">Generated Email:</h3>
                  <div className="bg-white border border-gray-300 rounded-lg p-4 max-h-64 overflow-y-auto">
                    <pre className="whitespace-pre-wrap text-sm text-gray-800">{generatedEmail}</pre>
                  </div>
                  <div className="flex space-x-2 mt-3">
                    <button
                      type="button"
                      onClick={() => navigator.clipboard.writeText(generatedEmail)}
                      className="flex-1 bg-blue-100 text-blue-700 py-2 px-4 rounded-lg font-medium hover:bg-blue-200 transition-colors"
                    >
                      Copy Email
                    </button>
                    <a
                      href={`mailto:${professor.email}?subject=Inquiry About Research Opportunities&body=${encodeURIComponent(generatedEmail)}`}
                      className="flex-1 bg-green-100 text-green-700 py-2 px-4 rounded-lg font-medium hover:bg-green-200 transition-colors text-center"
                    >
                      Send Email
                    </a>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ProfessorDetailPage;
