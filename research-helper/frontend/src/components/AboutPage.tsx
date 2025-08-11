import React, { useEffect, useState } from 'react';
import { TeamMember } from '../types';

// Import all team member images
import rishabImage from '../assets/images/rishab-suresh.jpg';
import royceImage from '../assets/images/royce-mathis.jpg';
import samkitImage from '../assets/images/samkit-bothra.jpg';
import aidanImage from '../assets/images/aidan-don.jpg'; // You'll need to add this image

const API_BASE = 'http://localhost:5050';

const teamMembers: TeamMember[] = [
  {
    name: 'Rishab Suresh',
    role: 'Co-Founder',
    bio: 'Rising senior in the IB Program at Seminole High School located in Central Florida',
    image: rishabImage,
    linkedin: 'https://www.linkedin.com/in/rishab-suresh22/'
  },
  {
    name: 'Royce Mathis',
    role: 'Co-Founder',
    bio: 'Rising senior in the IB Program at Seminole High School located in Central Florida',
    image: royceImage,
    linkedin: 'https://www.linkedin.com/in/roycejmathis/'
  },
  {
    name: 'Samkit Bothra',
    role: 'Co-Founder',
    bio: 'Rising senior dual enrolled at FAU located in South Florida',
    image: samkitImage,
    linkedin: 'https://www.linkedin.com/in/samkit-bothra/'
  },
  {
    name: 'Aidan Don',
    role: 'Social Media Manager & Design Lead',
    bio: 'Rising senior at Cooper City High School located in South Florida',
    image: aidanImage,
    linkedin: 'https://www.linkedin.com/in/aidankdon/'
  }
];

type Metrics = {
  students_connected: number;
  universities_covered: number;
  faculty_contacts: number;
};

const AboutPage: React.FC = () => {
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  useEffect(() => {
    let cancelled = false;

    // Fetch current metrics to render (visit is tracked globally in App.tsx)
    fetch(`${API_BASE}/metrics`, { credentials: 'include' })
      .then(r => r.json())
      .then(data => { if (!cancelled) setMetrics(data); })
      .catch(() => {
        if (!cancelled) {
          setMetrics({ students_connected: 0, universities_covered: 0, faculty_contacts: 0 });
        }
      });

    return () => { cancelled = true; };
  }, []);

  const n = (v?: number) => (typeof v === 'number' ? v.toLocaleString() : '—');

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 pt-20">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">About ResearchConnect</h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto">
            To unlock research opportunities for high school students by bridging access to university mentors and projects, cultivating a passion for discovery, and empowering all learners—regardless of background—to contribute to real academic inquiry.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-12 items-center mb-16">
          <div className="animate-slide-up">
            <h2 className="text-3xl font-bold text-gray-900 mb-6">Our Story</h2>
            <p className="text-lg text-gray-600 mb-6">
              ResearchConnect was born from the frustration of students struggling to find research opportunities. We realized that while talented students exist everywhere, connecting them with faculty members was unnecessarily difficult.
            </p>
            <p className="text-lg text-gray-600">
              Our platform bridges this gap by providing verified faculty contact information and intelligent matching based on research interests and academic backgrounds.
            </p>
          </div>

          <div className="glass p-8 rounded-2xl shadow-lg animate-slide-up">
            <h3 className="text-2xl font-bold text-gray-900 mb-6">Our Impact</h3>
            <div className="space-y-4">
              <div className="flex items-center">
                <div className="text-3xl font-bold text-blue-600 mr-4">
                  {n(metrics?.students_connected)}+
                </div>
                <div className="text-gray-600">Students Connected</div>
              </div>
              <div className="flex items-center">
                <div className="text-3xl font-bold text-purple-600 mr-4">
                  {n(metrics?.universities_covered)}+
                </div>
                <div className="text-gray-600">Universities Covered</div>
              </div>
              <div className="flex items-center">
                <div className="text-3xl font-bold text-green-600 mr-4">
                  {n(metrics?.faculty_contacts)}+
                </div>
                <div className="text-gray-600">Faculty Contacts</div>
              </div>
            </div>
          </div>
        </div>

        <div className="glass rounded-3xl shadow-2xl p-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-8 text-center">Meet Our Team</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {teamMembers.map((member, index) => (
              <div key={index} className="text-center animate-slide-up">
                <div className="w-32 h-32 mx-auto mb-4 rounded-full overflow-hidden shadow-lg">
                  <img
                    src={member.image}
                    alt={member.name}
                    className="w-full h-full object-cover"
                  />
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">{member.name}</h3>
                <p className="text-blue-600 font-semibold mb-3">{member.role}</p>
                <p className="text-gray-600 mb-4">{member.bio}</p>

                <a
                  href={member.linkedin}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center text-blue-600 hover:text-blue-800 transition-colors font-medium"
                >
                  <svg
                    className="w-5 h-5 mr-2"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.338 16.338H13.67V12.16c0-.995-.017-2.277-1.387-2.277-1.39 0-1.601 1.086-1.601 2.207v4.248H8.014v-8.59h2.559v1.174h.037c.356-.675 1.227-1.387 2.526-1.387 2.703 0 3.203 1.778 3.203 4.092v4.711zM5.005 6.575a1.548 1.548 0 11-.003-3.096 1.548 1.548 0 01.003 3.096zm-1.337 9.763H6.34v-8.59H3.667v8.59zM17.668 1H2.328C1.595 1 1 1.581 1 2.298v15.403C1 18.418 1.595 19 2.328 19h15.34c.734 0 1.332-.582 1.332-1.299V2.298C19 1.581 18.402 1 17.668 1z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Connect on LinkedIn
                </a>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AboutPage;
