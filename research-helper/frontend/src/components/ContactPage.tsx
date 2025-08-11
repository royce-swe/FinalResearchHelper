import React, { useState } from 'react';
import { ContactForm } from '../types';

const ContactPage: React.FC = () => {
  const [contactForm, setContactForm] = useState<ContactForm>({
    firstName: '',
    lastName: '',
    email: '',
    subject: '',
    message: ''
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleContactSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    
    const { firstName, lastName, email, subject, message } = contactForm;
    if (!firstName || !lastName || !email || !subject || !message) {
      alert('Please fill in all fields.');
      return;
    }

    setIsSubmitting(true);

    try {
      // Create form data for FormSubmit
      const formData = new FormData();
      formData.append('name', `${firstName} ${lastName}`);
      formData.append('email', email);
      formData.append('subject', `ResearchConnect Contact: ${subject}`);
      formData.append('message', message);
      formData.append('_next', window.location.href);
      formData.append('_captcha', 'false');
      formData.append('_template', 'table');
      formData.append('_autoresponse', 'Thank you for contacting ResearchConnect! We will get back to you soon.');

      const response = await fetch('https://formsubmit.co/researchconnect.ai@gmail.com', {
        method: 'POST',
        body: formData
      });

      if (response.ok) {
        // SUCCESS - Clear form and show success message
        setContactForm({
          firstName: '',
          lastName: '',
          email: '',
          subject: '',
          message: ''
        });
        alert("Thank you for your message! We'll get back to you soon.");
      } else {
        // HTTP ERROR - Form submission failed
        console.error('Form submission failed:', response.status, response.statusText);
        alert('There was an issue with the form. Please try emailing us directly using the contact information below.');
      }
    } 
    catch (error) {
      // NETWORK ERROR - Fetch failed completely
      console.error('Network error sending contact form:', error);
      alert('Network error. Please try emailing us directly using the contact information below.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const updateForm = (field: keyof ContactForm, value: string): void => {
    setContactForm(prev => ({ ...prev, [field]: value }));
  };

  // Generate mailto link with pre-filled subject and body
  const generateMailtoLink = () => {
    const subject = contactForm.subject || 'Inquiry about ResearchConnect';
    const body = contactForm.message ? 
      `Hi ResearchConnect Team,\n\n${contactForm.message}\n\nBest regards,\n${contactForm.firstName} ${contactForm.lastName}` :
      `Hi ResearchConnect Team,\n\n[Your message here]\n\nBest regards,\n[Your name]`;
    
    return `mailto:researchconnect.ai@gmail.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 pt-20">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-4">Get In Touch</h1>
          <p className="text-xl text-gray-600">
            Have questions? We'd love to hear from you. Choose your preferred way to contact us.
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Direct Contact Options - Left Column */}
          <div className="lg:col-span-1 space-y-6">
            {/* Email Contact */}
            <div className="glass rounded-2xl shadow-lg p-6">
              <div className="flex items-center mb-4">
                <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mr-4">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">Email Us</h3>
                  <p className="text-sm text-gray-600">Send us an email directly</p>
                </div>
              </div>
              <a 
                href={generateMailtoLink()}
                className="block w-full bg-blue-600 text-white text-center py-3 px-4 rounded-lg font-semibold hover:bg-blue-700 transition-colors"
              >
                Open Email App
              </a>
              <p className="text-sm text-gray-500 mt-3 text-center">
                researchconnect.ai@gmail.com
              </p>
            </div>

            {/* Quick Contact Info */}
            <div className="glass rounded-2xl shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <svg className="w-5 h-5 text-green-600 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Quick Info
              </h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center">
                  <span className="text-gray-600 w-20">Response:</span>
                  <span className="text-gray-900">Within 24 hours</span>
                </div>
                <div className="flex items-center">
                  <span className="text-gray-600 w-20">Best for:</span>
                  <span className="text-gray-900">General inquiries</span>
                </div>
                <div className="flex items-center">
                  <span className="text-gray-600 w-20">Support:</span>
                  <span className="text-gray-900">Technical issues</span>
                </div>
              </div>
            </div>

            {/* Social/Additional Contact */}
            <div className="glass rounded-2xl shadow-lg p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Other Ways to Connect</h3>
              <div className="space-y-3">
                <a 
                  href="mailto:researchconnect.ai@gmail.com?subject=Partnership Inquiry"
                  className="flex items-center text-gray-700 hover:text-blue-600 transition-colors"
                >
                  <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2-2v2m8 0V6a2 2 0 012 2v6a2 2 0 01-2 2H8a2 2 0 01-2-2V8a2 2 0 012-2h8z" />
                  </svg>
                  Partnership Opportunities
                </a>
                <a 
                  href="mailto:researchconnect.ai@gmail.com?subject=Technical Support"
                  className="flex items-center text-gray-700 hover:text-blue-600 transition-colors"
                >
                  <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  Technical Support
                </a>
                <a 
                  href="mailto:researchconnect.ai@gmail.com?subject=Feedback"
                  className="flex items-center text-gray-700 hover:text-blue-600 transition-colors"
                >
                  <svg className="w-4 h-4 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                  </svg>
                  General Feedback
                </a>
              </div>
            </div>
          </div>

          {/* Contact Form - Right Column */}
          <div className="lg:col-span-2">
            <div className="glass rounded-3xl shadow-2xl p-8 md:p-12">
              <div className="mb-8">
                <h2 className="text-3xl font-bold text-gray-900 mb-2">Send Us a Message</h2>
                <p className="text-gray-600">Fill out the form below and we'll get back to you as soon as possible.</p>
              </div>

              <form onSubmit={handleContactSubmit} className="space-y-6">
                <div className="grid md:grid-cols-2 gap-6">
                  <div>
                    <label htmlFor="firstName" className="block text-lg font-semibold text-gray-900 mb-2">
                      First Name
                    </label>
                    <input
                      type="text"
                      id="firstName"
                      name="firstName"
                      value={contactForm.firstName}
                      onChange={(e) => updateForm('firstName', e.target.value)}
                      className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:outline-none transition-colors"
                      placeholder="John"
                      disabled={isSubmitting}
                      required
                    />
                  </div>
                  <div>
                    <label htmlFor="lastName" className="block text-lg font-semibold text-gray-900 mb-2">
                      Last Name
                    </label>
                    <input
                      type="text"
                      id="lastName"
                      name="lastName"
                      value={contactForm.lastName}
                      onChange={(e) => updateForm('lastName', e.target.value)}
                      className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:outline-none transition-colors"
                      placeholder="Doe"
                      disabled={isSubmitting}
                      required
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="email" className="block text-lg font-semibold text-gray-900 mb-2">
                    Email
                  </label>
                  <input
                    type="email"
                    id="email"
                    name="email"
                    value={contactForm.email}
                    onChange={(e) => updateForm('email', e.target.value)}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:outline-none transition-colors"
                    placeholder="example@email.com"
                    disabled={isSubmitting}
                    required
                  />
                </div>

                <div>
                  <label htmlFor="subject" className="block text-lg font-semibold text-gray-900 mb-2">
                    Subject
                  </label>
                  <input
                    type="text"
                    id="subject"
                    name="subject"
                    value={contactForm.subject}
                    onChange={(e) => updateForm('subject', e.target.value)}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:outline-none transition-colors"
                    placeholder="What can we help you with?"
                    disabled={isSubmitting}
                    required
                  />
                </div>

                <div>
                  <label htmlFor="message" className="block text-lg font-semibold text-gray-900 mb-2">
                    Message
                  </label>
                  <textarea
                    id="message"
                    name="message"
                    value={contactForm.message}
                    onChange={(e) => updateForm('message', e.target.value)}
                    className="w-full px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:outline-none transition-colors"
                    placeholder="Tell us more about your inquiry..."
                    rows={5}
                    disabled={isSubmitting}
                    required
                  />
                </div>

                <div className="flex flex-col sm:flex-row gap-4 pt-4">
                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="flex-1 bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {isSubmitting ? 'Sending...' : 'Send Message'}
                  </button>
                  
                  <a
                    href={generateMailtoLink()}
                    className="flex-1 bg-gray-100 text-gray-700 py-3 px-6 rounded-lg font-semibold hover:bg-gray-200 transition-colors text-center border-2 border-gray-200 hover:border-gray-300"
                  >
                    Open in Email App
                  </a>
                </div>

                <div className="text-center text-sm text-gray-500 mt-4">
                  <p>Having trouble with the form? Use the "Open in Email App" button above or email us directly.</p>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ContactPage;