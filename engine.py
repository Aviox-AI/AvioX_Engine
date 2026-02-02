from datetime import datetime
import streamlit as st
from amadeus import Client
from openai import OpenAI
import json

# --- 1. INITIAL SETUP ---
try:
    AMADEUS_KEY = st.secrets["AMADEUS_KEY"]
    AMADEUS_SECRET = st.secrets["AMADEUS_SECRET"]
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except Exception as e:
    st.error(f"❌ Setup Error: Missing keys. ({e})")
    st.stop()

amadeus = Client(client_id=AMADEUS_KEY, client_secret=AMADEUS_SECRET)
ai_client = OpenAI(api_key=OPENAI_KEY)

# --- 2. PAGE CONFIG & STYLING ---
st.set_page_config(page_title="AvioX AI", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #020617;
    }
    
    .flight-card {
        background: #1e293b;
        padding: 0px; /* Reset for inner spacing */
        border-radius: 16px;
        border: 1px solid #334155;
        margin-bottom: 20px;
        color: white;
        overflow: hidden;
    }
    
    .card-body {
        padding: 25px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .card-footer {
        background: rgba(34, 211, 238, 0.05);
        border-top: 1px solid #334155;
        padding: 10px 25px;
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        color: #94a3b8;
    }

    .stButton>button { 
        background-color: #22d3ee; 
        color: #020617; 
        font-weight: 800; 
        border-radius: 8px;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. NAVBAR ---
nav_col1, nav_col2, nav_col3 = st.columns([1, 3, 1])
with nav_col1:
    st.markdown("<h1 style='color: #22d3ee; margin:0; font-size: 2.2rem;'>AvioX</h1>", unsafe_allow_html=True)
with nav_col2:
    user_query = st.text_input("", placeholder="Try 'London to Paris in April'...", label_visibility="collapsed")
with nav_col3:
    search_btn = st.button("Search", use_container_width=True)

# --- 4. SEARCH & FILTER LOGIC ---
if user_query:
    # We create a persistent session state for the flight data so filters don't trigger a re-search
    if search_btn:
        with st.spinner("AI Processing..."):
            sim_date = "2026-02-02"
            prompt = f"Convert to JSON: '{user_query}'. Rules: 3-letter IATA, YYYY-MM-DD. Today is {sim_date}. Return: {{\"origin\": \"CODE\", \"destination\": \"CODE\", \"date\": \"YYYY-MM-DD\"}}"
            ai_res = ai_client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0)
            st.session_state.search_data = json.loads(ai_res.choices[0].message.content)
            
            resp = amadeus.shopping.flight_offers_search.get(
                originLocationCode=st.session_state.search_data['origin'],
                destinationLocationCode=st.session_state.search_data['destination'],
                departureDate=st.session_state.search_data['date'],
                adults=1, max=20
            )
            st.session_state.flights = resp.data

    if 'flights' in st.session_state:
        # --- FILTER BAR ---
        st.markdown("### Refine Results")
        f1, f2, f3 = st.columns([1, 1, 2])
        with f1:
            sort_opt = st.selectbox("Sort By", ["Cheapest", "Highest Price"])
        with f2:
            stops_opt = st.selectbox("Stops", ["All", "Non-stop Only"])
        with f3:
            st.write(f"Showing flights for **{st.session_state.search_data['origin']} → {st.session_state.search_data['destination']}**")

        # --- APPLY PYTHON FILTERS ---
        display_flights = st.session_state.flights

        # Filter by Stops
        if stops_opt == "Non-stop Only":
            display_flights = [f for f in display_flights if len(f['itineraries'][0]['segments']) == 1]

        # Sort
        if sort_opt == "Cheapest":
            display_flights = sorted(display_flights, key=lambda x: float(x['price']['total']))
        else:
            display_flights = sorted(display_flights, key=lambda x: float(x['price']['total']), reverse=True)

        # --- 5. RESULTS DISPLAY ---
        for flight in display_flights:
            price = flight['price']['total']
            curr = flight['price']['currency']
            airline = flight['validatingAirlineCodes'][0]
            itinerary = flight['itineraries'][0]
            stops = len(itinerary['segments']) - 1
            stop_txt = "Non-stop" if stops == 0 else f"{stops} Stop(s)"
            
            dep = itinerary['segments'][0]['departure']['at'][11:16]
            arr = itinerary['segments'][-1]['arrival']['at'][11:16]
            dur = itinerary['duration'][2:].lower().replace('h', 'h ').replace('m', 'm')

            st.markdown(f"""
                <div class="flight-card">
                    <div class="card-body">
                        <div style="flex: 1;">
                            <img src="https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline.upper()}.svg" width="120" style="background:white; padding:8px; border-radius:8px;">
                        </div>
                        <div style="flex: 2; text-align: center;">
                            <span style="font-size: 2.2rem; font-weight: 800; letter-spacing: -1px;">{dep} &rarr; {arr}</span>
                        </div>
                        <div style="flex: 1; text-align: right;">
                            <span style="font-size: 2.2rem; font-weight: 800; color: #22d3ee;">{price} <small style="font-size: 1rem;">{curr}</small></span>
                        </div>
                    </div>
                    <div class="card-footer">
                        <span>🕒 Duration: <b>{dur}</b></span>
                        <span>✈️ <b>{stop_txt}</b></span>
                        <span style="color: #22d3ee; font-weight: bold;">{airline} Flight</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Select Flight {flight['id']}", key=f"btn_{flight['id']}", use_container_width=True):
                st.success(f"Confirming {airline} flight for {price} {curr}...")
