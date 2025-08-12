import React, { useEffect, useMemo, useState } from "react";

type DepartmentOption = { name: string; slug: string };
type UniversityOption = { name: string; slug: string; departments: DepartmentOption[] };

interface FacultyMember {
  id: string; // kept for Learn More
  name: string;
  email: string;
  title?: string;
  university: string;
  department: string;
}

interface FacultyFinderProps {
  onProfessorSelect: (professorId: string) => void;
}

const API_BASE = 'https://finalresearchhelper-production.up.railway.app';

const FacultyFinder: React.FC<FacultyFinderProps> = ({ onProfessorSelect }) => {
  // Options
  const [options, setOptions] = useState<UniversityOption[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [optionsError, setOptionsError] = useState<string | null>(null);

  // Selections
  const [selectedUniSlug, setSelectedUniSlug] = useState("");
  const [selectedDeptSlug, setSelectedDeptSlug] = useState("");

  // Results/UI
  const [facultyMembers, setFacultyMembers] = useState<FacultyMember[]>([]);
  const [displayCount, setDisplayCount] = useState(3);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  // Fetch dropdown options
  useEffect(() => {
    (async () => {
      try {
        setLoadingOptions(true);
        const res = await fetch(`${API_BASE}/options`);
        if (!res.ok) throw new Error("Failed to load options");
        const data = await res.json();
        setOptions(data.universities || []);
      } catch (e: any) {
        setOptionsError(e.message || "Failed to load options");
      } finally {
        setLoadingOptions(false);
      }
    })();
  }, []);

  // Departments for selected uni
  const departmentOptions: DepartmentOption[] = useMemo(() => {
    const uni = options.find((u) => u.slug === selectedUniSlug);
    return uni?.departments ?? [];
  }, [options, selectedUniSlug]);

  // Reset dept when uni changes
  useEffect(() => {
    setSelectedDeptSlug("");
  }, [selectedUniSlug]);

  // Fetch professors from CSV backend
  const fetchProfessors = async (
    uniSlug: string,
    deptSlug: string
  ): Promise<FacultyMember[] | null> => {
    try {
      const response = await fetch(`${API_BASE}/find-professors`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          university: uniSlug,     // folder name (e.g., "Caltech")
          department: deptSlug,    // file stem (e.g., "caltech_computer_science")
          max: 200,
        }),
      });

      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err?.error || "Server error while fetching data.");
      }

      const data = await response.json();

      const list: FacultyMember[] = (data.professors || []).map((p: any) => ({
        id: p.id || "",                    // must be supplied by backend to keep Learn More working
        name: p.name,
        email: p.email || "Not Available",
        title: p.title,
        university: p.university,
        department: p.department,
      }));

      return list;
    } catch (error) {
      console.error("Fetch failed:", error);
      setErrorMessage("Could not fetch professor data. Please try again.");
      return null;
    }
  };

  // Submit
  const handleSubmit = async () => {
    if (!selectedUniSlug || !selectedDeptSlug) {
      setErrorMessage("Please select both a university and a department.");
      return;
    }

    setIsLoading(true);
    setErrorMessage("");
    setFacultyMembers([]);
    setDisplayCount(3);

    const faculty = await fetchProfessors(selectedUniSlug, selectedDeptSlug);

    if (!faculty || faculty.length === 0) {
      setFacultyMembers([]);
      setErrorMessage("No matching professors found. Try another department.");
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
            Browse professors by university and department
          </p>
        </div>

        <div className="glass rounded-3xl shadow-2xl p-8 md:p-12">
          {loadingOptions ? (
            <p>Loading options…</p>
          ) : optionsError ? (
            <div className="bg-red-100 text-red-700 px-4 py-3 rounded-md">{optionsError}</div>
          ) : (
            <div className="space-y-8">
              {/* University */}
              <div>
                <label className="block text-2xl font-semibold text-gray-900 mb-4">
                  Select your university
                </label>
                <select
                  className="w-full px-6 py-4 text-lg border-2 border-gray-200 rounded-xl focus:border-blue-500 focus:outline-none transition-colors"
                  value={selectedUniSlug}
                  onChange={(e) => setSelectedUniSlug(e.target.value)}
                  required
                >
                  <option value="">Select a university…</option>
                  {options.map((u) => (
                    <option key={u.slug} value={u.slug}>
                      {u.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Department (appears after university selection) */}
              <div>
                <label className="block text-2xl font-semibold text-gray-900 mb-4">
                  Select department
                </label>
                <select
                  className="w-full px-6 py-4 text-lg border-2 border-gray-200 rounded-xl focus:border-purple-500 focus:outline-none transition-colors"
                  value={selectedDeptSlug}
                  onChange={(e) => setSelectedDeptSlug(e.target.value)}
                  disabled={!selectedUniSlug}
                  required
                >
                  {!selectedUniSlug ? (
                    <option value="">Choose a university first…</option>
                  ) : (
                    <>
                      <option value="">Select a department…</option>
                      {departmentOptions.map((d) => (
                        <option key={d.slug} value={d.slug}>
                          {d.name}
                        </option>
                      ))}
                    </>
                  )}
                </select>
              </div>

              {errorMessage && (
                <div className="bg-red-100 text-red-700 px-4 py-3 rounded-md">{errorMessage}</div>
              )}

              <button
                onClick={handleSubmit}
                disabled={!selectedUniSlug || !selectedDeptSlug || isLoading}
                className="w-full btn-primary text-xl py-4 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <span
                      className="animate-spin inline-block w-6 h-6 border-4 border-blue-600 border-t-transparent rounded-full mr-3"
                      aria-label="loading"
                    ></span>
                    Finding Professors...
                  </>
                ) : (
                  "Search →"
                )}
              </button>
            </div>
          )}

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
                            {faculty.title && (
                              <p className="text-sm text-gray-600">{faculty.title}</p>
                            )}
                            <p className="text-gray-600">{displayEmail}</p>
                            <p className="text-sm text-gray-500">
                              {faculty.university} • {faculty.department}
                            </p>
                          </div>
                        </div>
                        <div className="flex space-x-3">
                          {/* Quick Email button */}
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

                          {/* Learn More — unchanged */}
                          <button
                            onClick={() => onProfessorSelect(faculty.id)}
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
        </div>
      </div>
    </div>
  );
};

export default FacultyFinder;
