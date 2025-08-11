import requests
from bs4 import BeautifulSoup
import pandas as pd
#static html sight so we can simply use requests
url = 'https://www.cs.purdue.edu/graduate/admission/faculty.html'  

#fetch html and parse
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

#cerate list
data = []

#table with all info
table = soup.find('table', class_='directory table table-bordered table-striped table-condensed')

#the tag affiliated with each professor description is tr so we want to loop that
rows = table.find_all('tr')

#inside tr, each professor is attached to the td tag
for row in rows:
    cells = row.find_all('td')
    #the cells have columns we dont need
    if len(cells) >= 3:
        #name is in first cell
        name = cells[0].get_text(strip=True)

        #title is in second
        title = cells[1].get_text(strip=True)

        # Extract email from anchor in last cell if present
        email = 'N/A'
        #find the row with email as its not consecutive
        email_cell = row.find('a', href=True)
        #replace mailto which is autoadded
        if email_cell and 'mailto:' in email_cell['href']:
            email = email_cell['href'].replace('mailto:', '').strip()
        #append all three items to list
        data.append({
            'Name': name,
            'Title': title,
            'Email': email
        })

#use pandas to convert to dataframe and save as csv
df = pd.DataFrame(data)
df.to_csv('purdue_faculty.csv', index=False)
