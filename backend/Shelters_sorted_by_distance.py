from bs4 import BeautifulSoup
import re

# Load your HTML file
with open("/Users/naren/Documents/Python/DubHacks/foodbanks_map.html", "r", encoding="utf-8") as f:
    html_content = f.read()

soup = BeautifulSoup(html_content, "html.parser")

# Find all popup HTML content in the script tags
popups = soup.find_all("script")

# Regex pattern to extract shelter info from popup HTML
pattern = re.compile(
    r"<b>(.*?)</b>.*?<i>(.*?)</i>.*?Distance:</b>\s*([\d\.]+)?\s*km",
    re.DOTALL
)

shelters = []

for script in popups:
    matches = pattern.findall(str(script))
    for match in matches:
        name = match[0].strip()
        address = match[1].strip()
        distance_str = match[2].strip()
        distance_km = float(distance_str) if distance_str else None
        shelters.append({
            "name": name,
            "address": address,
            "distance_km": distance_km
        })

# Filter out shelters without distance (optional)
shelters_with_distance = [s for s in shelters if s["distance_km"] is not None]

# Sort by distance
shelters_sorted = sorted(shelters_with_distance, key=lambda x: x["distance_km"])

# Display sorted shelters
for s in shelters_sorted:
    print(f"{s['name']} - {s['address']} - {s['distance_km']} km")
