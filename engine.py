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

# Cache the client to prevent "Stale Token" errors
@st.cache_resource
def get_amadeus_client():
    return Client(client_id=AMADEUS_KEY, client_secret=AMADEUS_SECRET)

amadeus = get_amadeus_client()
ai_client = OpenAI(api_key=OPENAI_KEY)

# --- 2. PAGE CONFIG & SKYSCANNER THEME ---
st.set_page_config(page_title="AvioX AI", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    .stApp { background-color: #f1f2f8; }

    /* Navbar Alignment */
    .nav-wrapper {
        display: flex;
        align-items: center;
        gap: 20px;
        padding: 15px 0;
    }

    .flight-card {
        background: white;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(37,32,31,.3);
        margin-bottom: 12px;
        color: #25201f;
    }
    
    .card-body { padding: 20px 30px; display: flex; align-items: center; justify-content: space-between; }
    .card-footer {
        background: #fbfcfd;
        border-top: 1px solid #eee;
        padding: 10px 30px;
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        color: #68697f;
        border-radius: 0 0 8px 8px;
    }

    .stButton>button { 
        background-color: #0062E3 !important; 
        color: white !important; 
        font-weight: 700; 
        border-radius: 4px;
        border: none;
        height: 45px;
    }
    
    /* Aligning the Input box height */
    .stTextInput>div>div>input {
        height: 45px !important;
        border-radius: 4px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. ALIGNED NAVBAR (Centered & Larger) ---
# We use [2, 5, 1.2] to give the logo a generous "cell" for centering
nav_col1, nav_col2, nav_col3 = st.columns([2, 5, 1.2])

with nav_col1:
    # This HTML uses flexbox to center the logo text in the gap
    st.markdown("""
        <div style="display: flex; 
                    justify-content: center; 
                    align-items: center; 
                    height: 65px; 
                    width: 100%;">
            <h1 style='color: #0062E3; 
                       margin: 0; 
                       font-size: 3.5rem; 
                       font-weight: 900; 
                       letter-spacing: -2px;
                       line-height: 1;'>
                Avio<span style='color: #25201f;'>X</span>
            </h1>
        </div>
    """, unsafe_allow_html=True)

with nav_col2:
    # Adjusted padding to 15px to line up with the 3.5rem logo
    st.markdown("<div style='padding-top: 15px;'>", unsafe_allow_html=True)
    user_query = st.text_input("", placeholder="Where to?", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

with nav_col3:
    st.markdown("<div style='padding-top: 15px;'>", unsafe_allow_html=True)
    search_btn = st.button("Search", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("---")

# --- 4. SEARCH & FILTER LOGIC ---
if user_query:
    # 1. Trigger the AI and Amadeus fetch ONLY when button is pressed
    if search_btn:
        with st.spinner("Analyzing route and fetching prices..."):
            try:
                # Use simulated date for Test API
                sim_date = "2026-02-02"
                prompt = f"Convert to JSON: '{user_query}'. Return ONLY: {{\"origin\": \"CODE\", \"destination\": \"CODE\", \"date\": \"YYYY-MM-DD\"}}"
                
                ai_res = ai_client.chat.completions.create(
                    model="gpt-3.5-turbo", 
                    messages=[{"role": "user", "content": prompt}], 
                    temperature=0
                )
                
                # Save data to session state so it survives refreshes
                st.session_state.search_data = json.loads(ai_res.choices[0].message.content)
                
                # Fetch flights
                origin_code = st.session_state.search_data['origin'].upper()
                dest_code = st.session_state.search_data['destination'].upper()
                
                resp = amadeus.shopping.flight_offers_search.get(
                    originLocationCode=origin_code,
                    destinationLocationCode=dest_code,
                    departureDate=st.session_state.search_data['date'],
                    adults=1, 
                    max=15
                )
                st.session_state.flights = resp.data
                
            except Exception as e:
                st.error(f"Engine Error: {e}")

    # 2. Display results if they exist in memory
    if 'flights' in st.session_state and 'search_data' in st.session_state:
        # --- REFINED FILTER BAR ---
        with st.container():
            f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
            with f1:
                sort_opt = st.selectbox("Sort by", ["Cheapest", "Highest Price"])
            with f2:
                stops_opt = st.selectbox("Stops", ["All", "Non-stop Only"])
            with f3:
                st.selectbox("Cabin", ["Economy", "Premium", "Business"], disabled=True)
            with f4:
                # Use session_state to safely display origin/destination
                origin_disp = st.session_state.search_data['origin'].upper()
                dest_disp = st.session_state.search_data['destination'].upper()
                st.markdown(f"<p style='padding-top:35px; color:#68697f;'>Results for <b>{origin_disp} to {dest_disp}</b></p>", unsafe_allow_html=True)

        # --- DATA PROCESSING (Sorting & Filtering) ---
        display_flights = st.session_state.flights
        
        # Filter by stops
        if stops_opt == "Non-stop Only":
            display_flights = [f for f in display_flights if len(f['itineraries'][0]['segments']) == 1]
        
        # Sort by price
        is_reverse = (sort_opt == "Highest Price")
        display_flights = sorted(display_flights, key=lambda x: float(x['price']['total']), reverse=is_reverse)

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
                                <div style="color: #68697f; font-size: 0.9rem;">{st.session_state.search_data['origin'].upper()}</div>
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
                                <div style="color: #68697f; font-size: 0.9rem;">{st.session_state.search_data['destination'].upper()}</div>
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
            
            if st.button(f"Select Flight {flight['id']}", key=f"btn_{flight['id']}", use_container_width=True):
                st.success(f"Confirming {airline} flight for {price} {curr}...")
