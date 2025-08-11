#making http requests
import httpx
#parses html
from bs4 import BeautifulSoup
#dataframe
import pandas as pd

url = 'https://research.gatech.edu/data/faculty'
response = httpx.get(url)

#convert to html parser
soup = BeautifulSoup(response.text, 'html.parser')


data = []
#looks for all li tags because inspect element showed us that the text we need are wrapped in li tags
faculty_rows = soup.find_all('div', class_='views-row')

for row in faculty_rows:
    # Extract name
    name = 'N/A'
    name_tag = row.find('div', class_='views-field views-field-title')
    if name_tag:
        name_link = name_tag.find('a')
        if name_link:
            name = name_link.get_text(strip=True)

    # Extract title
    title = 'N/A'
    title_tag = row.find('div', class_='views-field views-field-field-title')
    if title_tag:
        strong_tag = title_tag.find('strong')
        if strong_tag:
            title = strong_tag.get_text(strip=True)

    # Extract email (optional)
    email = 'N/A'
    email_tag = row.find('div', class_='views-field views-field-field-email-contact')
    if email_tag:
        email_content = email_tag.find('div', class_='field-content')
        if email_content:
            email = email_content.get_text(strip=True)

    data.append({
        'Name': name,
        'Title': title,
        'Email': email
    })

    
df = pd.DataFrame(data)

# Save to CSV
df.to_csv('gt_faculty.csv', index=False)