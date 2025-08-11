#making http requests
import httpx
#parses html
from bs4 import BeautifulSoup
#dataframe
import pandas as pd

url = 'https://siebelschool.illinois.edu/about/people/all-faculty'
response = httpx.get(url)

#convert to html parser
soup = BeautifulSoup(response.text, 'html.parser')

data = []

#name of the block in inspect e that has all the people
faculty_blocks = soup.find_all('div', class_='item person cat15 cs')

for faculty in faculty_blocks:
    #extrct name
    name = 'N/A'
    # div tag that has the specific name of a professor
    name_tag = faculty.find('div', class_='name')
    #get the name from the a tag
    if name_tag:
        name = name_tag.a.get_text(strip=True)

    #extract title
    title = 'N/A'
    #div tag that has specfici title of a professor
    title_tag = faculty.find('div', class_='title')
    #get the title from inside the div tag
    if title_tag:
        title = title_tag.get_text(strip=True)

    #email is hidden in div tag email hide-empty as data-value so we access that here
    email = 'N/A'
    email_tag = faculty.find('div', class_='email hide-empty')
    if email_tag:
        email = email_tag['data-value']

    data.append({
        'Name': name,
        'Title': title,
        'Email': email
    })

# Output as DataFrame and CSV
df = pd.DataFrame(data)
df.to_csv('uiuc_faculty.csv', index=False)