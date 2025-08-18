import React from 'react';
import { Link } from 'react-router-dom';

const Footer: React.FC = () => {
  return (
    <footer className="bg-gray-900 text-white py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid md:grid-cols-4 gap-8">
          <div>
            <div className="text-2xl font-bold gradient-text mb-4">
              ResearchConnect
            </div>
            <p className="text-gray-400">
              Connecting students with research opportunities at top universities worldwide.
            </p>
          </div>
          
          <div>
            <h3 className="font-semibold text-lg mb-4">Product</h3>
            <div className="space-y-2">
              <Link 
                to="/finder" 
                className="block text-gray-400 hover:text-white transition-colors"
              >
                Faculty Finder
              </Link>
              <a href="#" className="block text-gray-400 hover:text-white transition-colors">
                Research Database
              </a>
              <a href="#" className="block text-gray-400 hover:text-white transition-colors">
                Email Templates
              </a>
            </div>
          </div>
          
          <div>
            <h3 className="font-semibold text-lg mb-4">Company</h3>
            <div className="space-y-2">
              <Link 
                to="/about" 
                className="block text-gray-400 hover:text-white transition-colors"
              >
                About Us
              </Link>
              <Link 
                to="/contact" 
                className="block text-gray-400 hover:text-white transition-colors"
              >
                Contact
              </Link>
              <a href="#" className="block text-gray-400 hover:text-white transition-colors">
                Careers
              </a>
            </div>
          </div>
          
          <div>
            <h3 className="font-semibold text-lg mb-4">Connect</h3>
            <div className="space-y-2">
              <a 
                href="https://instagram.com/researchconnect.ai" 
                target="_blank" 
                rel="noopener noreferrer"
                className="block text-gray-400 hover:text-white transition-colors"
              >
                Instagram
              </a>
            </div>
          </div>
        </div>
        
        <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
          <p>&copy; 2025 ResearchConnect. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
