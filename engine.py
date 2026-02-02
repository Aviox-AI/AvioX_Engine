from datetime import datetime
import streamlit as st
from amadeus import Client
from openai import OpenAI
import json

# --- 1. SETUP & KEYS ---
try:
    AMADEUS_KEY = st.secrets["AMADEUS_KEY"]
    AMADEUS_SECRET = st.secrets["AMADEUS_SECRET"]
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except Exception as e:
    st.error(f"❌ Setup Error: Missing keys. ({e})")
    st.stop()

@st.cache_resource
def get_clients():
    return Client(client_id=AMADEUS_KEY, client_secret=AMADEUS_SECRET), OpenAI(api_key=OPENAI_KEY)

amadeus, ai_client = get_clients()

# --- 2. CONFIG & CSS (THE FIX) ---
st.set_page_config(page_title="AvioX | Elite Travel", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    .stApp { background-color: #F8F9FC; }
    
    /* --- NAVBAR FIX --- */
    /* This forces the Logo, Input, and Button to align perfectly */
    .nav-container {
        display: flex;
        align-items: center;
        gap: 20px;
        padding-bottom: 20px;
        border-bottom: 1px solid #EEF0F6;
        margin-bottom: 30px;
    }
    
    /* Make the input box taller and cleaner */
    .stTextInput div[data-baseweb="input"] {
        height: 55px;
        border-radius: 12px;
        border: 2px solid #E2E8F0;
        background-color: white;
    }
    
    /* Make the Search Button match the Input box height */
    .stButton button {
        height: 55px !important;
        border-radius: 12px !important;
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        background-color: #0062E3 !important;
        color: white !important;
        border: none !important;
        width: 100%;
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        background-color: #0051C0 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(0,98,227,0.2);
    }

    /* --- FLIGHT CARD FIX --- */
    .flight-card {
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border: 1px solid #EEF0F6;
        margin-bottom: 20px;
        overflow: hidden; /* Keeps content inside rounded corners */
        transition: transform 0.2s ease;
    }
    .flight-card:hover {
        transform: translateY(-3px);
        border-color: #0062E3;
        box-shadow: 0 10px 30px rgba(0,98,227,0.1);
    }
    
    .card-body { padding: 30px; display: flex; align-items: center; }
    
    .card-footer {
        background: #F8FAFC;
        padding: 15px 30px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-top: 1px solid #EEF0F6;
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 500;
    }

    /* The "Select" button inside the card */
    .select-btn-container {
        width: 100%;
        margin-top: 0px;
    }
    .select-btn-container button {
        border-radius: 0 0 16px 16px !important; /* Round bottom corners only */
        margin-top: -1px !important;
    }
    
    /* Route Visualizer Line */
    .route-line {
        position: relative; 
        height: 2px; 
        background: #E2E8F0; 
        width: 100%; 
        margin: 10px 0;
    }
    .plane-icon {
        position: absolute; 
        top: -12px; 
        left: 50%; 
        transform: translateX(-50%); 
        background: white; 
        padding: 0 8px; 
        font-size: 1.2rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR (Shortlist) ---
with st.sidebar:
    st.markdown("### 🔖 Saved Flights")
    if 'shortlist' not in st.session_state: st.session_state.shortlist = []

    if not st.session_state.shortlist:
        st.info("Your shortlist is empty.")
    else:
        for item in st.session_state.shortlist:
            st.markdown(f"""
                <div style="background: white; padding: 15px; border-radius: 10px; border: 1px solid #EEF0F6; margin-bottom: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);">
                    <div style="font-weight: 700; color: #1E293B;">{item['airline']}</div>
                    <div style="font-size: 0.85rem; color: #64748B;">{item['route']}</div>
                    <div style="font-size: 1.1rem; font-weight: 800; color: #0062E3; margin-top: 5px;">{item['price']} {item['curr']}</div>
                </div>
            """, unsafe_allow_html=True)
        if st.button("Clear List"):
            st.session_state.shortlist = []
            st.rerun()

# --- 4. ALIGNED HEADER ---
# We use st.columns with 'vertical_alignment' (if supported) or just clean ratios
c1, c2, c3 = st.columns([2, 5, 1.5], gap="medium")

with c1:
    # Logo
    st.markdown("""
        <h1 style='color: #0062E3; margin: 0; padding-top: 5px; font-size: 3rem; font-weight: 900; letter-spacing: -2px; line-height: 1;'>
            Avio<span style='color: #1E293B;'>X</span>
        </h1>
    """, unsafe_allow_html=True)

with c2:
    # Input
    user_query = st.text_input("", placeholder="Try 'NYC to London in October'", label_visibility="collapsed")

with c3:
    # Search Button
    search_pressed = st.button("Search Flights", use_container_width=True)

st.markdown("<div style='margin-bottom: 30px;'></div>", unsafe_allow_html=True)

# --- 5. LOGIC ENGINE ---
if user_query and search_pressed:
    with st.spinner("Scanning global routes..."):
        try:
            # AI Parsing
            today = datetime.now().strftime("%Y-%m-%d")
            prompt = f"""
            Extract entities from: '{user_query}'.
            Return ONLY raw JSON: {{"origin": "IATA_CODE", "destination": "IATA_CODE", "date": "YYYY-MM-DD"}}
            Reference Date: {today}.
            """
            
            ai_res = ai_client.chat.completions.create(
                model="gpt-3.5-turbo", 
                messages=[{"role": "user", "content": prompt}], 
                temperature=0
            )
            
            clean_json = ai_res.choices[0].message.content.replace('```json', '').replace('```', '').strip()
            st.session_state.search_meta = json.loads(clean_json)
            
            # Amadeus API
            resp = amadeus.shopping.flight_offers_search.get(
                originLocationCode=st.session_state.search_meta['origin'].upper(),
                destinationLocationCode=st.session_state.search_meta['destination'].upper(),
                departureDate=st.session_state.search_meta['date'],
                adults=1, max=15
            )
            st.session_state.flights = resp.data
            
        except Exception as e:
            st.error(f"Search Error: {e}")

# --- 6. RESULTS RENDERING ---
if 'flights' in st.session_state and st.session_state.flights:
    # Top Bar
    meta = st.session_state.search_meta
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
            <div style="font-size: 1.2rem; font-weight: 700; color: #1E293B;">
                Flights from {meta['origin']} to {meta['destination']}
            </div>
            <div style="color: #64748B;">Found {len(st.session_state.flights)} options</div>
        </div>
    """, unsafe_allow_html=True)

    # Process Data
    df = st.session_state.flights
    df = sorted(df, key=lambda x: float(x['price']['total'])) # Sort by cheapest
    min_price = float(df[0]['price']['total'])

    for idx, flight in enumerate(df):
        # Extract Variables
        price = float(flight['price']['total'])
        curr = flight['price']['currency']
        airline = flight['validatingAirlineCodes'][0]
        it = flight['itineraries'][0]
        
        dep_time = it['segments'][0]['departure']['at'][11:16]
        arr_time = it['segments'][-1]['arrival']['at'][11:16]
        
        # Duration Formatting
        raw_dur = it['duration'][2:].lower() # PT12H30M -> 12H30M
        dur = raw_dur.replace('h', 'h ').replace('m', 'm')
        
        stops = len(it['segments']) - 1
        
        # Color Logic (CALCULATED IN PYTHON, NOT HTML)
        stop_color = "#059669" if stops == 0 else "#EF4444"
        stop_text = "Direct" if stops == 0 else f"{stops} Stop(s)"
        
        # HTML Rendering
        st.markdown(f"""
            <div class="flight-card">
                <div class="card-body">
                    <div style="flex: 1;">
                        <img src="https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline.upper()}.svg" width="100" style="margin-bottom: 8px;">
                        <div style="font-size: 0.8rem; color: #64748B; font-weight: 600;">Operated by {airline}</div>
                    </div>

                    <div style="flex: 3; display: flex; align-items: center; gap: 40px; margin: 0 30px;">
                        <div style="text-align: right;">
                            <div style="font-size: 1.8rem; font-weight: 800; color: #1E293B; line-height: 1;">{dep_time}</div>
                            <div style="color: #64748B; font-size: 1rem; font-weight: 600; margin-top: 4px;">{meta['origin']}</div>
                        </div>
                        
                        <div style="text-align: center; flex: 1;">
                            <div style="font-size: 0.85rem; color: #64748B; font-weight: 600; margin-bottom: 6px;">{dur}</div>
                            <div class="route-line">
                                <div class="plane-icon">✈️</div>
                            </div>
                            <div style="font-size: 0.85rem; margin-top: 8px; font-weight: 700; color: {stop_color};">
                                {stop_text}
                            </div>
                        </div>

                        <div style="text-align: left;">
                            <div style="font-size: 1.8rem; font-weight: 800; color: #1E293B; line-height: 1;">{arr_time}</div>
                            <div style="color: #64748B; font-size: 1rem; font-weight: 600; margin-top: 4px;">{meta['destination']}</div>
                        </div>
                    </div>

                    <div style="flex: 1; text-align: right; border-left: 1px solid #F1F5F9; padding-left: 30px;">
                        {f'<div style="background:#ECFDF5; color:#059669; border:1px solid #A7F3D0; padding:4px 8px; border-radius:4px; font-size:0.7rem; font-weight:700; display:inline-block; margin-bottom:5px;">BEST PRICE</div>' if price == min_price else ''}
                        <div style="font-size: 0.85rem; color: #64748B; font-weight: 500;">Per adult</div>
                        <div style="font-size: 2.2rem; font-weight: 800; color: #0F172A; letter-spacing: -1px;">{price:.0f} <small style="font-size: 1.1rem; color: #64748B; font-weight: 600;">{curr}</small></div>
                    </div>
                </div>
                
                <div class="card-footer">
                    <div style="display: flex; gap: 20px;">
                        <span>🛍️ <b>Personal Item</b> included</span>
                        <span>🔄 <b>Flexible</b> rebooking</span>
                    </div>
                    <div style="color: #0062E3; font-weight: 700;">Flight Details &rarr;</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Select Button (Full Width, Attached to Card)
        if st.button(f"Select Flight {idx}", key=f"btn_{idx}", use_container_width=True):
            st.session_state.shortlist.append({
                "airline": airline,
                "price": price,
                "curr": curr,
                "route": f"{meta['origin']} → {meta['destination']}"
            })
            st.toast(f"✅ Added {airline} flight to your shortlist!")
            st.rerun()

elif 'flights' in st.session_state:
    st.info("No flights found. Try a major route like LHR to JFK.")
