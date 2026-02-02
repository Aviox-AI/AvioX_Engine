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

# Cache Amadeus client to prevent session timeouts
@st.cache_resource
def get_amadeus_client():
    return Client(client_id=AMADEUS_KEY, client_secret=AMADEUS_SECRET)

amadeus = get_amadeus_client()
ai_client = OpenAI(api_key=OPENAI_KEY)

# --- 2. PAGE CONFIG & THEME ---
st.set_page_config(page_title="AvioX AI", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    .stApp { background-color: #f1f2f8; }

    /* Modern Flight Card */
    .flight-card {
        background: white;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(37,32,31,.1);
        margin-bottom: 15px;
        color: #25201f;
        border: 1px solid transparent;
        transition: all 0.2s ease;
    }
    .flight-card:hover {
        border-color: #0062E3;
        box-shadow: 0 4px 12px rgba(0,98,227,0.15);
    }
    
    .card-body { padding: 25px 35px; display: flex; align-items: center; justify-content: space-between; }
    
    .card-footer {
        background: #fbfcfd;
        border-top: 1px solid #eee;
        padding: 12px 35px;
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        color: #68697f;
        border-radius: 0 0 12px 12px;
    }

    /* Primary Button */
    .stButton>button { 
        background-color: #0062E3 !important; 
        color: white !important; 
        font-weight: 700; 
        border-radius: 6px;
        border: none;
        height: 50px;
        font-size: 1.1rem;
    }
    
    /* Input Styling */
    .stTextInput>div>div>input {
        height: 50px !important;
        border-radius: 6px !important;
        font-size: 1.1rem !important;
    }

    /* Flight Timeline UI */
    .timeline-container {
        display: flex;
        align-items: center;
        gap: 15px;
        color: #68697f;
    }
    .timeline-line {
        flex-grow: 1;
        height: 2px;
        background: #ddd;
        position: relative;
        min-width: 80px;
    }
    .timeline-plane {
        position: absolute;
        top: -9px;
        left: 45%;
        background: white;
        padding: 0 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. PRO NAVBAR ---
nav_col1, nav_col2, nav_col3 = st.columns([2, 5, 1.2])

with nav_col1:
    st.markdown("""
        <div style="display: flex; align-items: center; height: 70px;">
            <h1 style='color: #0062E3; margin: 0; font-size: 3.5rem; font-weight: 900; letter-spacing: -2px;'>
                Avio<span style='color: #25201f;'>X</span>
            </h1>
        </div>
    """, unsafe_allow_html=True)

with nav_col2:
    st.markdown("<div style='padding-top: 18px;'>", unsafe_allow_html=True)
    user_query = st.text_input("", placeholder="e.g. London to Paris in October", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

with nav_col3:
    st.markdown("<div style='padding-top: 18px;'>", unsafe_allow_html=True)
    search_btn = st.button("Search", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# --- 4. ENGINE LOGIC ---
if user_query:
    if search_btn:
        with st.spinner("AvioX is scanning the skies..."):
            try:
                # Use a reliable date for the Test API
                sim_date = "2026-02-02"
                prompt = f"""Return ONLY raw JSON. No markdown. 
                Convert: '{user_query}'. 
                Format: {{"origin": "IATA", "destination": "IATA", "date": "YYYY-MM-DD"}}
                Today is {sim_date}. If no year is mentioned, use 2026."""
                
                ai_res = ai_client.chat.completions.create(
                    model="gpt-3.5-turbo", 
                    messages=[{"role": "user", "content": prompt}], 
                    temperature=0
                )
                
                # Clean AI response for robust JSON parsing
                clean_json = ai_res.choices[0].message.content.replace('```json', '').replace('```', '').strip()
                st.session_state.search_data = json.loads(clean_json)
                
                # API Call
                resp = amadeus.shopping.flight_offers_search.get(
                    originLocationCode=st.session_state.search_data['origin'].upper(),
                    destinationLocationCode=st.session_state.search_data['destination'].upper(),
                    departureDate=st.session_state.search_data['date'],
                    adults=1, max=25
                )
                st.session_state.flights = resp.data
                
            except Exception as e:
                if hasattr(e, 'response') and e.response:
                    try:
                        detail = e.response.result['errors'][0]['detail']
                        st.error(f"✈️ Amadeus: {detail}")
                    except: st.error(f"Error: {e}")
                else: st.error(f"System Error: {e}")

    # --- 5. RESULTS & FILTERS ---
    if 'flights' in st.session_state and 'search_data' in st.session_state:
        # Filter Bar
        f1, f2, f3, f4 = st.columns([1, 1, 1, 2])
        with f1:
            sort_opt = st.selectbox("Sort by", ["Cheapest", "Fastest", "Highest Price"])
        with f2:
            stops_opt = st.selectbox("Stops", ["All", "Direct Only"])
        with f3:
            st.selectbox("Cabin", ["Economy"], disabled=True)
        with f4:
            st.markdown(f"<p style='padding-top:35px; color:#68697f; text-align:right;'>Showing flights for <b>{st.session_state.search_data['origin'].upper()} to {st.session_state.search_data['destination'].upper()}</b></p>", unsafe_allow_html=True)

        # Processing
        df = st.session_state.flights
        if stops_opt == "Direct Only":
            df = [f for f in df if len(f['itineraries'][0]['segments']) == 1]
        
        if sort_opt == "Cheapest":
            df = sorted(df, key=lambda x: float(x['price']['total']))
        elif sort_opt == "Highest Price":
            df = sorted(df, key=lambda x: float(x['price']['total']), reverse=True)

        # Rendering
        for flight in df:
            price = flight['price']['total']
            curr = flight['price']['currency']
            airline = flight['validatingAirlineCodes'][0]
            it = flight['itineraries'][0]
            stops = len(it['segments']) - 1
            stop_txt = "Direct" if stops == 0 else f"{stops} stop"
            dep = it['segments'][0]['departure']['at'][11:16]
            arr = it['segments'][-1]['arrival']['at'][11:16]
            dur = it['duration'][2:].lower().replace('h', 'h ').replace('m', 'm')

            st.markdown(f"""
                <div class="flight-card">
                    <div class="card-body">
                        <div style="flex: 1;">
                            <img src="https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline.upper()}.svg" width="110">
                            <div style="font-size: 0.8rem; color: #68697f; margin-top: 5px; font-weight: 600;">{airline}</div>
                        </div>
                        
                        <div style="flex: 3; display: flex; justify-content: center; align-items: center; gap: 40px; margin: 0 20px;">
                            <div style="text-align: right;">
                                <div style="font-size: 1.6rem; font-weight: 700;">{dep}</div>
                                <div style="color: #68697f; font-size: 0.9rem;">{st.session_state.search_data['origin'].upper()}</div>
                            </div>
                            
                            <div style="text-align: center; min-width: 150px;">
                                <div style="font-size: 0.85rem; color: #68697f; margin-bottom: 4px;">{dur}</div>
                                <div class="timeline-container">
                                    <div class="timeline-line">
                                        <span class="timeline-plane">✈️</span>
                                    </div>
                                </div>
                                <div style="font-size: 0.85rem; margin-top: 4px; color: {'#00a698' if stops==0 else '#d32f2f'}; font-weight: 600;">{stop_txt}</div>
                            </div>

                            <div style="text-align: left;">
                                <div style="font-size: 1.6rem; font-weight: 700;">{arr}</div>
                                <div style="color: #68697f; font-size: 0.9rem;">{st.session_state.search_data['destination'].upper()}</div>
                            </div>
                        </div>

                        <div style="flex: 1; text-align: right; border-left: 1px solid #eee; padding-left: 20px;">
                            <div style="font-size: 0.85rem; color: #68697f;">Best Price</div>
                            <div style="font-size: 1.8rem; font-weight: 800; color: #25201f;">{price} <small style="font-size: 1rem;">{curr}</small></div>
                            <div style="font-size: 0.7rem; color: #00a698; font-weight: 600;">Includes taxes & fees</div>
                        </div>
                    </div>
                    <div class="card-footer">
                        <span>✨ Professional Choice &middot; Flexible Rebooking Available</span>
                        <span style="color: #0062E3; font-weight: 700; cursor: pointer;">View Details &rarr;</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Select Flight {flight['id']}", key=f"btn_{flight['id']}", use_container_width=True):
                st.success(f"Seat held for {price} {curr}. Completing booking...")
