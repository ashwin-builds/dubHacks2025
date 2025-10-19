import pandas as pd
df = pd.read_csv('user_information.csv', sep = "|")
names = df['Name']
print(names)
addresses = df['Address']
cat = df['Categories']
print(addresses)

foodbanks = [

]

for i in range(len(names)):
  foodbanks.append({'name':names[i], 'address':addresses[i], 'categories':cat[i]})


print(foodbanks)

import folium
from geopy.geocoders import Nominatim
from folium.plugins import MeasureControl
import openrouteservice
import time

user_location = (47.6075017, -122.3319142)


client = openrouteservice.Client(key='REPLACE WITH KEY') #REPLACE WITH KEY OR LOAD KEY IN

def get_lat_lon(address):
    loc = Nominatim(user_agent="Geopy Library")
    getLoc = loc.geocode(address)
    time.sleep(1)  
    if getLoc:
        return getLoc.latitude, getLoc.longitude
    else:
        return None, None

def plot_map(foodbanks):
    m = folium.Map(location=user_location, zoom_start=12, width='100%', height='80%')
    
    for fb in foodbanks:
        lat, lon = get_lat_lon(fb["address"])
        if lat is None or lon is None:
            continue
    
        if fb['categories'] == 'Food':
            map_icon = "cutlery"
        elif fb['categories'] == 'Shelter':
            map_icon = "bed"
        else:
            map_icon = "info-sign"
        

        coords = ((user_location[1], user_location[0]), (lon, lat)) 
        try:
            route = client.directions(coords)
            distance_m = route['routes'][0]['summary']['distance']  
            duration_s = route['routes'][0]['summary']['duration']  
            distance_km = round(distance_m/1000, 2)
            duration_min = round(duration_s/60, 1)
            popup_text = f"""
            <div style="font-size: 14pt; line-height: 1.5; max-width: 300px;">
                <b>{fb['name']}</b><br>
                <i>{fb['address']}</i><br>
                <b>Distance:</b> {distance_km} km<br>
                <b>Travel Time:</b> {duration_min} min
            </div>
            """
        except:
            popup_text = f"""
            <div style="font-size: 14pt; line-height: 1.5; max-width: 300px;">
                <b>{fb['name']}</b><br>
                <i>{fb['address']}</i><br>
                Distance/Time not available
            </div>
            """
        
        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_text, max_width=350),
            icon=folium.Icon(color="red", icon=map_icon, prefix="fa")
        ).add_to(m)
    
    m.add_child(MeasureControl(primary_length_unit='kilometers'))
    
    return m

plot_map(foodbanks)