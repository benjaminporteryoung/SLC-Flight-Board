import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd

# This sets up the look of the web page
st.set_page_config(page_title="SLC Terminal A Flights", page_icon="🛫", layout="centered")

def is_target_gate(gate_str):
    if not gate_str or not isinstance(gate_str, str):
        return False
    if not gate_str.startswith('A'):
        return False
    try:
        gate_num = int(gate_str[1:])
        return gate_num >= 38
    except ValueError:
        return False

def clean_cell(td):
    strings = list(td.stripped_strings)
    return strings[0] if strings else "N/A"

# The @st.cache_data tells the website to hold onto the data for 5 minutes (300 seconds) 
# so the SLC servers don't get overwhelmed if all your coworkers open the app at once.
@st.cache_data(ttl=300)
def get_flight_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    flights = []
    now = datetime.now()
    seen_pm = False
    
    for page in range(40):
        url = f"https://slcairport.com/airlines-flights/arrivals-departures/?query_leg=D&page={page}"
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            rows = soup.find_all('tr')
            
            if len(rows) <= 1:
                break
                
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    time_str = clean_cell(cols[0])
                    destination = clean_cell(cols[1])
                    flight_num = clean_cell(cols[2])
                    status = clean_cell(cols[3])
                    gate = clean_cell(cols[4])
                    
                    if 'PM' in time_str:
                        seen_pm = True
                    if seen_pm and 'AM' in time_str:
                        return flights 
                    
                    if is_target_gate(gate):
                        sort_key = datetime.max 
                        try:
                            clean_time = time_str.replace('*', '').strip()
                            parsed_time = datetime.strptime(clean_time, "%I:%M %p")
                            flight_time = parsed_time.replace(year=now.year, month=now.month, day=now.day)
                            sort_key = flight_time
                            
                            if flight_time < now and ("Scheduled" in status or "On Time" in status):
                                status = "Departed"
                                
                        except ValueError:
                            pass
                            
                        flights.append({
                            'TIME': time_str,
                            'FLIGHT': flight_num,
                            'DESTINATION': destination,
                            'GATE': gate,
                            'STATUS': status,
                            'sort_key': sort_key
                        })
        except Exception:
            break 
            
    return flights

# --- Web Page Design ---
st.title("🛫 SLC Terminal A (Gates A38+)")
st.write("Live closing-shift departures. Data pulled directly from SLC Airport Systems.")

with st.spinner('Scanning all pages of the SLC flight database...'):
    current_flights = get_flight_data()

if not current_flights:
    st.warning("No flights currently listed for the specified gates.")
else:
    # Sort chronologically
    current_flights.sort(key=lambda x: x['sort_key'])
    
    # Convert our list into a Pandas DataFrame (a fancy table that looks great on mobile)
    df = pd.DataFrame(current_flights)
    df = df.drop(columns=['sort_key'])
    
    # Display the table on the website
    st.dataframe(df, hide_index=True, use_container_width=True)

st.caption("This board refreshes automatically every 5 minutes. You can also pull down on your phone screen to manually refresh.")
