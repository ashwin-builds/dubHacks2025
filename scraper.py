import requests
from bs4 import BeautifulSoup

def create_soup(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    return soup

soup = create_soup('https://search.wa211.org/en/search?query=BH-1800.8500-150&query_label=Overnight+Shelters&query_type=taxonomy&location=King+County%2C+Washington%2C+United+States&coords=-122.297622%2C47.59526')
titles_soup = soup.find_all(class_="font-semibold leading-none tracking-tight flex flex-row justify-between gap-2")
descriptions_soup = soup.find_all(class_ = "whitespace-break-spaces print:hidden")

titles = []
descriptions = []
links = []
addresses = []
ph_numbers = []


for title in titles_soup:
    titles.append(title.text)

for description in descriptions_soup:
    descriptions.append(description.text)

for organization_detail in soup.find_all(class_ = "flex flex-col items-start justify-start gap-2"):
    children = organization_detail.contents
    link = children[0].text
    address = children[1].text
    ph_number = children[2].text
    
    links.append(link)
    addresses.append(address)
    ph_numbers.append(ph_number)

with open('user_information.csv', 'w') as f:
    f.write('Name|Password|Description|Address|Phone Number|Link\n')

with open('user_information.csv', 'a') as f:
    for i in range(len(titles)):
        f.write(titles[i] + '|' + '|'+ descriptions[i] + '|' + addresses[i] + '|' + ph_numbers[i] + '|' + links[i] + "\n")

