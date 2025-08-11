import httpx
from bs4 import BeautifulSoup
import pandas as pd

url = 'https://www.cs.stanford.edu/people-cs/faculty-name'
#retrieve html info from webpage so we can parse info from it
response = httpx.get(url)

#convert to html parser
soup = BeautifulSoup(response.text, 'html.parser')

#create list
data = []

#name of the block in inspect e that has all the people
for li in soup.find_all('li'):
    
    #tag that has the specific name of a professor
    name_tag = li.find('h3')
    #get the name from the a tag
    if name_tag:
        name = name_tag.get_text(strip=True)
    else:
        continue

    # Extract title
    title_tag = li.find('div', class_='node stanford-person su-person-short-title string label-hidden')
    title = title_tag.get_text(strip=True) if title_tag else 'N/A'

    # Extract profile link
    link_tag = li.find('a', href=True)
    profile_link = 'N/A'
    if link_tag:
        profile_link = 'https://www.cs.stanford.edu' + link_tag['href']

    # Now visit the profile page and extract email
    email = 'N/A'
    if profile_link != 'N/A':
        profile_resp = httpx.get(profile_link)
        profile_soup = BeautifulSoup(profile_resp.text, 'html.parser')
        email_div = profile_soup.find('div', class_='su-person-email')
        if email_div:
            email_tag = email_div.find('a', href=True)
            if email_tag and 'mailto:' in email_tag['href']:
                email = email_tag['href'].replace('mailto:', '').strip()

    # Append to dataset
    data.append({
        'name': name,
        'title': title,
        'email': email
    })

# Save to CSV
df = pd.DataFrame(data)
df.to_csv('stanford_faculty.csv', index=False)
