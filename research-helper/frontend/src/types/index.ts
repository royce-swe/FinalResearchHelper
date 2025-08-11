export interface ContactForm {
  firstName: string;
  lastName: string;
  email: string;
  subject: string;
  message: string;
}

export interface TeamMember {
  name: string;
  role: string;
  bio: string;
  image: string;
  linkedin: string;
}

export interface Feature {
  title: string;
  description: string;
  icon: string;
}

export type PageType = 'home' | 'finder' | 'about' | 'contact' | 'professor-detail';