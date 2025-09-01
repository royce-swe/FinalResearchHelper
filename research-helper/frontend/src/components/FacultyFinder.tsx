import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

interface FacultyMember {
  id: string;
  name: string;
  email: string;
  title?: string;
  university: string;
  department: string;
}

//const API_BASE = "https://finalresearchhelper-production.up.railway.app";
const API_BASE = "http://localhost:5050";

const FacultyFinder: React.FC = () => {
  const navigate = useNavigate();

  const [fieldOfStudy, setFieldOfStudy] = useState("");
  const [targetUniversity, setTargetUniversity] = useState("");
  const [facultyMembers, setFacultyMembers] = useState<FacultyMember[]>([]);
  const [displayCount, setDisplayCount] = useState(3);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const fetchGPTProfessors = async (
    field: string,
    school: string
  ): Promise<FacultyMember[] | null> => {
    try {
      const response = await fetch(`${API_BASE}/gptprofessorsearch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          field: field.trim(),
          school: school.trim(),
        }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err?.error || "Server error while fetching GPT professors.");
      }

      const data = await response.json();
      const list: FacultyMember[] = (data.professors || []).map((p: any) => ({
        id: p.id || "",
        name: p.name,
        email: p.email || "Not Available",
        title: p.title,
        university: p.university,
        department: p.department,
      }));

      return list;
    } catch (error) {
      console.error("GPT fetch failed:", error);
      setErrorMessage("Could not fetch professor data. Please try again later.");
      return null;
    }
  };

  const handleSubmit = async () => {
    const token = localStorage.getItem('research_helper_token');
    if (!token) {
      // Not logged in → redirect to login page
      navigate('/login');
      return;
    }
  
    // Proceed with your current search logic
    if (!fieldOfStudy.trim() && !targetUniversity.trim()) {
      setErrorMessage("Please enter at least a field of study or a university.");
      return;
    }
  
    setIsLoading(true);
    setErrorMessage("");
    setFacultyMembers([]);
    setDisplayCount(3);
  
    const faculty = await fetchGPTProfessors(fieldOfStudy, targetUniversity);
  
    if (!faculty || faculty.length === 0) {
      setFacultyMembers([]);
      setErrorMessage("No matching professors found. Try a different query.");
    } else {
      setFacultyMembers(faculty);
    }
  
    setIsLoading(false);
  };
  

  const handleLoadMore = () => setDisplayCount((prev) => prev + 3);
  const visibleProfessors = facultyMembers.slice(0, displayCount);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 pt-20">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">Faculty Finder</h1>
          <p className="text-xl text-gray-600">
            Find professors by field of study and university
          </p>
        </div>

        <div className="glass rounded-3xl shadow-2xl p-8 md:p-12 space-y-8">
          {/* Field of Study */}
          <div>
            <label className="block text-2xl font-semibold text-gray-900 mb-4">
              What's your field of study?
            </label>
            <input
              type="text"
              value={fieldOfStudy}
              onChange={(e) => setFieldOfStudy(e.target.value)}
              placeholder="e.g., Artificial Intelligence"
              className="w-full px-6 py-4 text-lg border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none transition-colors"
            />
          </div>

          {/* Target University */}
          <div>
            <label className="block text-2xl font-semibold text-gray-900 mb-4">
              Select your target university
            </label>
            <input
              type="text"
              value={targetUniversity}
              onChange={(e) => setTargetUniversity(e.target.value)}
              placeholder="e.g., Caltech"
              className="w-full px-6 py-4 text-lg border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none transition-colors"
            />
          </div>

          {errorMessage && (
            <div className="bg-red-100 text-red-700 px-4 py-3 rounded-md">{errorMessage}</div>
          )}

          <button
            onClick={handleSubmit}
            disabled={isLoading}
            className="w-full btn-primary text-xl py-4 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "Finding Professors..." : "Search →"}
          </button>

          {/* Results */}
          {visibleProfessors.length > 0 && (
            <div className="mt-12 p-8 bg-gradient-to-r from-gray-50 to-blue-50 rounded-2xl border border-gray-200">
              <h3 className="text-2xl font-bold text-gray-900 mb-6 text-center flex items-center justify-center">
                <span className="mr-2">📧</span>
                Professors Found
              </h3>
              <div className="space-y-4">
                {visibleProfessors.map((faculty) => {
                  const hasValidEmail =
                    faculty.email &&
                    faculty.email !== "Not Available" &&
                    faculty.email !== "N/A";
                  const displayEmail = hasValidEmail ? faculty.email : "N/A";

                  return (
                    <div
                      key={`${faculty.university}-${faculty.department}-${faculty.name}`}
                      className="bg-white p-6 rounded-lg shadow-sm border-l-4 border-blue-500 hover:shadow-md transition-shadow duration-200"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center flex-1">
                          <span className="text-2xl mr-4">👨‍🏫</span>
                          <div>
                            <h4 className="text-lg font-semibold text-gray-900">{faculty.name}</h4>
                            {faculty.title && <p className="text-sm text-gray-600">{faculty.title}</p>}
                            <p className="text-gray-600">{displayEmail}</p>
                            <p className="text-sm text-gray-500">
                              {faculty.university} • {faculty.department}
                            </p>
                          </div>
                        </div>
                        <div className="flex space-x-3">
                          <a
                            href={hasValidEmail ? `mailto:${faculty.email}` : "#"}
                            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                              hasValidEmail
                                ? "bg-gray-100 text-gray-700 hover:bg-gray-200"
                                : "bg-gray-300 text-gray-400 cursor-not-allowed"
                            }`}
                            onClick={(e) => {
                              if (!hasValidEmail) e.preventDefault();
                            }}
                            tabIndex={hasValidEmail ? 0 : -1}
                            aria-disabled={!hasValidEmail}
                          >
                            Quick Email
                          </a>
                          <button
                          onClick={() => {
                            const openAlexId = faculty.id.split('/').pop();

                            // Open a new tab with query params (email passed here)
                            const email = encodeURIComponent(faculty.email || "");
                            window.open(`/professors/${openAlexId}?email=${email}`, "_blank", "noopener,noreferrer");
                          }}
                            className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition-colors"
                          >
                            Learn More →
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {displayCount < facultyMembers.length && (
                <button
                  onClick={handleLoadMore}
                  disabled={isLoading}
                  className="w-full mt-6 bg-white text-gray-700 py-3 px-6 rounded-lg font-semibold hover:bg-gray-50 transition-colors border-2 border-gray-200 hover:border-blue-300 disabled:opacity-50"
                >
                  Load More Professors
                </button>
              )}
            </div>
          )}
          {isLoading && (
            <div className="flex justify-center items-center mt-8">
              <div className="animate-spin w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full"></div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FacultyFinder;
