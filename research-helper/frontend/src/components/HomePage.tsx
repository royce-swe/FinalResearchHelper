import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Feature } from '../types';

const words = [
  'Assistant.',
  'Helper.',
  'Partner.',
  'Companion.',
  'Navigator.',
  'Ally.',
];

const features: Feature[] = [
  {
    title: 'Smart Matching',
    description: 'Our AI-powered system matches you with faculty based on your field of study and research interests.',
    icon: '🎯'
  },
  {
    title: 'Verified Contacts',
    description: 'Access up-to-date, verified faculty contact information from top universities worldwide.',
    icon: '✅'
  },
  {
    title: 'Easy Outreach',
    description: 'Get personalized email templates and tips to make meaningful connections with researchers.',
    icon: '📧'
  }
];

const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const [displayedText, setDisplayedText] = useState('');
  const [wordIndex, setWordIndex] = useState(0);
  const [charIndex, setCharIndex] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    const currentWord = words[wordIndex];
    const typingSpeed = isDeleting ? 40 : 80;

    const timeout = setTimeout(() => {
      if (isDeleting) {
        setDisplayedText(currentWord.substring(0, charIndex - 1));
        setCharIndex((prev) => prev - 1);
      } else {
        setDisplayedText(currentWord.substring(0, charIndex + 1));
        setCharIndex((prev) => prev + 1);
      }

      if (!isDeleting && charIndex === currentWord.length) {
        setTimeout(() => setIsDeleting(true), 1500);
      }

      if (isDeleting && charIndex === 0) {
        setIsDeleting(false);
        setWordIndex((prev) => (prev + 1) % words.length);
      }
    }, typingSpeed);

    return () => clearTimeout(timeout);
  }, [charIndex, isDeleting, wordIndex]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Hero Section */}
      <div className="pt-20 pb-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <div className="mb-8">
              <h1 className="text-6xl md:text-7xl font-bold text-gray-900 mb-4">
                Research
                <span className="gradient-text">
                  <em> {displayedText}</em>
                </span>
                <span className="animate-pulse text-blue-500">|</span>
              </h1>
            </div>
            <p className="text-xl md:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto">
              Connect with faculty members at top universities. Find your perfect research mentor and kickstart your academic journey.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={() => navigate('/finder')}
                className="btn-primary text-lg px-8 py-4 rounded-full"
              >
                Find Faculty →
              </button>
              <button
                onClick={() => navigate('/about')}
                className="btn-secondary text-lg px-8 py-4 rounded-full"
              >
                Learn More
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="py-16 bg-white/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">Why Choose ResearchConnect?</h2>
            <p className="text-xl text-gray-600">Streamline your research journey with our powerful tools</p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="glass p-8 rounded-2xl shadow-lg hover:shadow-xl transition-all duration-300 animate-slide-up"
              >
                <div className="text-4xl mb-4 text-center">{feature.icon}</div>
                <h3 className="text-2xl font-bold text-gray-900 mb-4 text-center">{feature.title}</h3>
                <p className="text-gray-600 text-center">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
