import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import pytz

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

@st.cache_data(ttl=300)
def get_flight_data():
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    flights = []
    
    # Permanently anchor the server's "now" clock to Utah (Mountain Time)
    mt_tz = pytz.timezone('America/Denver')
    now = datetime.now(mt_tz)
    
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
                        sort_key = now # Default fallback
                        try:
                            clean_time = time_str.replace('*', '').strip()
                            parsed_time = datetime.strptime(clean_time, "%I:%M %p")
                            
                            # Construct the flight time explicitly in Mountain Time
                            flight_time = mt_tz.localize(datetime(now.year, now.month, now.day, parsed_time.hour, parsed_time.minute))
                            sort_key = flight_time
                            
                            # Compare the Mountain Time flight against the Mountain Time "now"
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

st.title("🛫 SLC Terminal A (Gates A38+)")
st.write("Live closing-shift departures. Data pulled directly from SLC Airport Systems.")

with st.spinner('Scanning all pages of the SLC flight database...'):
    current_flights = get_flight_data()

if not current_flights:
    st.warning("No flights currently listed for the specified gates.")
else:
    current_flights.sort(key=lambda x: x['sort_key'])
    
    df = pd.DataFrame(current_flights)
    df = df.drop(columns=['sort_key'])
    
    st.dataframe(df, hide_index=True, use_container_width=True)

st.caption("This board refreshes automatically every 5 minutes. You can also pull down on your phone screen to manually refresh.")
