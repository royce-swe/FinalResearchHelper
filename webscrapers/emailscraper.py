import requests
from bs4 import BeautifulSoup
import openai
import re
import time

# === CONFIGURATION ===
openai.api_key = "your-openai-api-key"

student = {
    "name": "Royce Mathis",
    "grade": "Junior",
    "program": "IB",
    "interests": ["machine learning", "computer engineering"],
    "skills": ["Python", "Java", "data analysis"],
    "github": "https://github.com/royce-swe",
    "location": "remote",
    "preferred_universities": ["MIT", "Stanford", "Harvard"]
}

# === Scraping Utilities ===
def scrape_professors(university_url):
    try:
        response = requests.get(university_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        professors = []

        for tag in soup.find_all(['p', 'li', 'div'], string=re.compile(r'@')):
            text = tag.get_text(" ", strip=True)
            email_match = re.search(r"[\w\.-]+@[\w\.-]+", text)
            name_match = re.search(r"Dr\.?\s+[A-Z][a-z]+\s+[A-Z][a-z]+|Professor\s+[A-Z][a-z]+\s+[A-Z][a-z]+", text)
            if email_match and name_match:
                professors.append({
                    "name": name_match.group(),
                    "email": email_match.group(),
                    "university": university_url,
                    "research_area": "",
                    "recent_paper": ""
                })
        return professors
    except Exception as e:
        print(f"Error scraping {university_url}: {e}")
        return []

# === Placeholder for Academic Paper Fetching ===
def fetch_recent_paper(prof_name):
    time.sleep(1)  # Simulate API delay
    return "Recent Advances in Deep Learning Models"

# === Email Generation ===
def generate_email(student, professor):
    prompt = f"""
    You are an AI assistant that writes professional, personalized emails from high school students to professors.

    Student Info:
    Name: {student['name']}
    Grade: {student['grade']}
    Program: {student['program']}
    Interests: {', '.join(student['interests'])}
    Skills: {', '.join(student['skills'])}
    GitHub: {student['github']}

    Professor Info:
    Name: {professor['name']}
    Email: {professor['email']}
    University: {professor['university']}
    Research Area: {professor['research_area']}
    Recent Paper: {professor['recent_paper']}

    Write a personalized outreach email in 1st person (from student), no more than 3 short paragraphs.
    """

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You write polite and tailored research emails."},
            {"role": "user", "content": prompt}
        ]
    )
    return response["choices"][0]["message"]["content"].strip()

# === Execution ===
if __name__ == "__main__":
    department_pages = {
        "MIT": "https://www.eecs.mit.edu/people/faculty-advisors/",
        "Stanford": "https://cs.stanford.edu/directory/faculty",
        "Harvard": "https://www.seas.harvard.edu/computer-science/people/faculty"
    }

    all_professors = []
    for uni in student['preferred_universities']:
        url = department_pages.get(uni)
        if url:
            scraped = scrape_professors(url)
            for prof in scraped:
                prof['research_area'] = student['interests'][0]  # Placeholder for demo
                prof['recent_paper'] = fetch_recent_paper(prof['name'])
            all_professors.extend(scraped)

    for prof in all_professors[:3]:
        print("============================")
        print(f"To: {prof['email']}")
        print(generate_email(student, prof))
        print("\n")
