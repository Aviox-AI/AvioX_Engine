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

# --- 2. PAGE CONFIG & SKYSCANNER THEME ---
st.set_page_config(page_title="AvioX AI", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Relative:wght@400;700&family=Inter:wght@400;600;700&display=swap');
    
    /* Overall Background */
    .stApp {
        background-color: #f1f2f8; /* Light gray-blue background like Skyscanner */
    }

    /* Navbar Alignment */
    .nav-container {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 10px 0;
        margin-bottom: 20px;
    }

    /* Modern Flight Card */
    .flight-card {
        background: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(37,32,31,.3);
        margin-bottom: 12px;
        color: #25201f;
        border: none;
    }
    
    .card-body {
        padding: 20px 30px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .card-footer {
        background: #fbfcfd;
        border-top: 1px solid #ddd;
        padding: 8px 30px;
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        color: #68697f;
        border-radius: 0 0 8px 8px;
    }

    /* Skyscanner Blue Buttons */
    .stButton>button { 
        background-color: #0062E3 !important; 
        color: white !important; 
        font-weight: 700; 
        border-radius: 4px;
        border: none;
        padding: 10px 20px;
        transition: 0.2s;
    }
    .stButton>button:hover {
        background-color: #004fb8 !important;
    }

    /* Input styling */
    .stTextInput>div>div>input {
        background-color: white !important;
        border: 1px solid #ddd !important;
        border-radius: 4px !important;
        height: 45px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ALIGNED NAVBAR (Logo & Search) ---
# We use a custom HTML container for perfect vertical centering
nav_col1, nav_col2, nav_col3 = st.columns([1, 4, 1])

with nav_col1:
    # Adjusted logo size and vertical alignment
    st.markdown("<h1 style='color: #0062E3; margin-top: 5px; font-size: 1.8rem; font-weight: 800;'>AvioX</h1>", unsafe_allow_html=True)

with nav_col2:
    # Search bar now sits on the same horizontal plane
    user_query = st.text_input("", placeholder="Where to? (e.g. London to Paris)", label_visibility="collapsed")

with nav_col3:
    search_btn = st.button("Search", use_container_width=True)

# --- 4. SEARCH & FILTER LOGIC ---
if user_query:
    if search_btn:
        with st.spinner("Searching..."):
            sim_date = "2026-02-02"
            prompt = f"Convert to JSON: '{user_query}'. Return: {{\"origin\": \"CODE\", \"destination\": \"CODE\", \"date\": \"YYYY-MM-DD\"}}"
            ai_res = ai_client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0)
            st.session_state.search_data = json.loads(ai_res.choices[0].message.content)
            
            resp = amadeus.shopping.flight_offers_search.get(
                originLocationCode=st.session_state.search_data['origin'],
                destinationLocationCode=st.session_state.search_data['destination'],
                departureDate=st.session_state.search_data['date'],
                adults=1, max=15
            )
            st.session_state.flights = resp.data

    if 'flights' in st.session_state:
        # --- REFINED FILTER BAR ---
        # Centering the filter bar on a lighter background
        with st.container():
            f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
            with f1:
                sort_opt = st.selectbox("Sort by", ["Cheapest", "Highest Price"], label_visibility="visible")
            with f2:
                stops_opt = st.selectbox("Stops", ["All", "Non-stop Only"], label_visibility="visible")
            with f3:
                # Placeholder for class/airline
                st.selectbox("Cabin", ["Economy", "Premium", "Business"], disabled=True)
            with f4:
                st.markdown(f"<p style='padding-top:35px; color:#68697f;'>Results for <b>{st.session_state.search_data['origin']} to {st.session_state.search_data['destination']}</b></p>", unsafe_allow_html=True)

        # --- DATA PROCESSING ---
        display_flights = st.session_state.flights
        if stops_opt == "Non-stop Only":
            display_flights = [f for f in display_flights if len(f['itineraries'][0]['segments']) == 1]
        
        display_flights = sorted(display_flights, key=lambda x: float(x['price']['total']), reverse=(sort_opt == "Highest Price"))

        # --- 5. SKYSCANNER-STYLE RESULTS ---
        for flight in display_flights:
            price = flight['price']['total']
            curr = flight['price']['currency']
            airline = flight['validatingAirlineCodes'][0]
            itinerary = flight['itineraries'][0]
            stops = len(itinerary['segments']) - 1
            stop_txt = "Direct" if stops == 0 else f"{stops} stop"
            
            dep = itinerary['segments'][0]['departure']['at'][11:16]
            arr = itinerary['segments'][-1]['arrival']['at'][11:16]
            dur = itinerary['duration'][2:].lower().replace('h', 'h ').replace('m', 'm')

            st.markdown(f"""
                <div class="flight-card">
                    <div class="card-body">
                        <div style="flex: 1;">
                            <img src="https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline.upper()}.svg" width="100" style="opacity: 0.9;">
                        </div>
                        <div style="flex: 3; display: flex; justify-content: space-around; align-items: center; border-left: 1px solid #eee; border-right: 1px solid #eee; margin: 0 40px;">
                            <div style="text-align: center;">
                                <div style="font-size: 1.4rem; font-weight: 700;">{dep}</div>
                                <div style="color: #68697f; font-size: 0.9rem;">{st.session_state.search_data['origin']}</div>
                            </div>
                            <div style="text-align: center; color: #68697f; min-width: 100px;">
                                <div style="font-size: 0.8rem;">{dur}</div>
                                <div style="border-bottom: 2px solid #ddd; margin: 5px 0; position: relative;">
                                    <span style="position: absolute; top: -5px; left: 45%; background: white; padding: 0 5px;">✈</span>
                                </div>
                                <div style="font-size: 0.8rem; color: {'#00a698' if stops==0 else '#d32f2f'};">{stop_txt}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 1.4rem; font-weight: 700;">{arr}</div>
                                <div style="color: #68697f; font-size: 0.9rem;">{st.session_state.search_data['destination']}</div>
                            </div>
                        </div>
                        <div style="flex: 1; text-align: right;">
                            <div style="font-size: 0.8rem; color: #68697f;">Best Price</div>
                            <div style="font-size: 1.6rem; font-weight: 800; color: #25201f;">{price} <small>{curr}</small></div>
                        </div>
                    </div>
                    <div class="card-footer">
                        <span>Managed by {airline} &middot; Eco-friendly choice available</span>
                        <span style="color: #0062E3; font-weight: bold;">Flight Details &rarr;</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            # The "Select" button now looks more integrated
            if st.button(f"Select Flight {flight['id']}", key=f"btn_{flight['id']}", use_container_width=True):
                st.success(f"Proceeding with {airline} at {price} {curr}")
