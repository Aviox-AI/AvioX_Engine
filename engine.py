from datetime import datetime
import streamlit as st
from amadeus import Client
from openai import OpenAI
import json

# --- 1. CONFIGURATION & KEYS ---
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

# --- 2. THE DESIGN SYSTEM (CSS) ---
st.set_page_config(page_title="AvioX | Elite Travel", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    .stApp { background-color: #F8FAFC; font-family: 'Plus Jakarta Sans', sans-serif; }
    
    /* --- NAVBAR ALIGNMENT FIX --- */
    /* Forces the Search Button to be the exact same height as the Input box */
    div.stButton > button {
        height: 52px !important;
        margin-top: 0px !important;
        border-radius: 12px !important;
        background-color: #0062E3 !important;
        color: white !important;
        font-weight: 700 !important;
        border: none !important;
    }
    
    /* Input box styling */
    div[data-baseweb="input"] {
        height: 52px !important;
        border-radius: 12px !important;
        border: 2px solid #E2E8F0 !important;
        background-color: white !important;
    }

    /* --- FLIGHT CARD CONTAINER --- */
    .flight-card {
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        border: 1px solid #F1F5F9;
        margin-bottom: 24px;
        overflow: hidden;
        transition: transform 0.2s ease;
    }
    .flight-card:hover {
        border-color: #0062E3;
        transform: translateY(-2px);
        box-shadow: 0 12px 30px rgba(0,98,227,0.1);
    }
    
    .card-content { padding: 30px; display: flex; align-items: center; }
    
    .card-bottom {
        background: #F8FAFC;
        padding: 12px 30px;
        border-top: 1px solid #F1F5F9;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 600;
    }

    /* --- VISUALIZER --- */
    .visual-container {
        flex: 3;
        display: flex;
        align-items: center;
        gap: 20px;
        margin: 0 40px;
    }
    .time-big { font-size: 1.8rem; font-weight: 800; color: #0F172A; line-height: 1; }
    .city-code { font-size: 1rem; color: #94A3B8; font-weight: 700; margin-top: 5px; }
    
    .path-line {
        flex: 1;
        height: 2px;
        background: #E2E8F0;
        position: relative;
        border-radius: 2px;
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

    /* --- BADGES --- */
    .badge-best {
        background: #ECFDF5;
        color: #059669;
        border: 1px solid #A7F3D0;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        display: inline-block;
        margin-bottom: 5px;
    }
    
    /* --- ACTION BUTTON --- */
    .select-btn-wrapper button {
        width: 100%;
        border-radius: 0 0 16px 16px !important;
        margin-top: -1px !important;
        height: 50px !important;
        z-index: 10;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR (Shortlist) ---
with st.sidebar:
    st.markdown("### ✈️ Trip Planner")
    if 'shortlist' not in st.session_state: st.session_state.shortlist = []
    
    if st.session_state.shortlist:
        for item in st.session_state.shortlist:
            st.markdown(f"""
                <div style="padding:12px; background:white; border-radius:8px; border:1px solid #E2E8F0; margin-bottom:8px;">
                    <div style="font-weight:700; color:#1E293B;">{item['airline']}</div>
                    <div style="font-size:0.8rem; color:#64748B;">{item['route']}</div>
                    <div style="font-weight:700; color:#0062E3; margin-top:4px;">{item['price']} {item['curr']}</div>
                </div>
            """, unsafe_allow_html=True)
        if st.button("Clear Planner"):
            st.session_state.shortlist = []
            st.rerun()
    else:
        st.info("Your planner is empty.")

# --- 4. ALIGNED HEADER ---
# We use accurate column ratios to keep elements tight
c1, c2, c3 = st.columns([1.5, 5, 1.2])

with c1:
    st.markdown("""
        <h1 style='color: #0062E3; margin: 0; padding-top: 5px; font-size: 2.8rem; font-weight: 900; letter-spacing: -2px; line-height: 1;'>
            Avio<span style='color: #1E293B;'>X</span>
        </h1>
    """, unsafe_allow_html=True)

with c2:
    # Padding top 8px aligns the input box center-to-center with the Logo text
    st.markdown("<div style='padding-top: 8px;'>", unsafe_allow_html=True)
    user_query = st.text_input("", placeholder="e.g. London to Dubai in November", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    # Padding top 8px aligns the button with the input box
    st.markdown("<div style='padding-top: 8px;'>", unsafe_allow_html=True)
    search_pressed = st.button("Search", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 40px;'></div>", unsafe_allow_html=True)

# --- 5. LOGIC ENGINE ---
if user_query and search_pressed:
    with st.spinner("Analyzing global routes..."):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            prompt = f"Return JSON: {{\"origin\": \"IATA\", \"destination\": \"IATA\", \"date\": \"YYYY-MM-DD\"}} for '{user_query}'. Today: {today}"
            
            ai_res = ai_client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0)
            clean_json = ai_res.choices[0].message.content.replace('```json', '').replace('```', '').strip()
            st.session_state.search_meta = json.loads(clean_json)
            
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
    
    # Sort Data
    df = sorted(st.session_state.flights, key=lambda x: float(x['price']['total']))
    min_price = float(df[0]['price']['total'])

    for idx, flight in enumerate(df):
        # --- PREPARE VARIABLES (No Logic in HTML) ---
        price = float(flight['price']['total'])
        currency = flight['price']['currency']
        airline = flight['validatingAirlineCodes'][0]
        it = flight['itineraries'][0]
        
        dep_time = it['segments'][0]['departure']['at'][11:16]
        arr_time = it['segments'][-1]['arrival']['at'][11:16]
        
        raw_dur = it['duration'][2:].lower()
        dur_str = raw_dur.replace('h', 'h ').replace('m', 'm')
        
        stops = len(it['segments']) - 1
        
        # Determine Colors/Text based on stops
        if stops == 0:
            stop_label = "Direct"
            stop_color = "#059669"
            stop_bg = "#ECFDF5"
        else:
            stop_label = f"{stops} Stop"
            stop_color = "#EF4444"
            stop_bg = "#FEF2F2"
            
        # Determine Badge
        badge_html = ""
        if price == min_price:
            badge_html = f'<div class="badge-best">BEST PRICE</div>'
        
        # Logo URL
        logo_url = f"https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline}.svg"

        # --- RENDER HTML ---
        st.markdown(f"""
            <div class="flight-card">
                <div class="card-content">
                    <div style="flex:1;">
                        <img src="{logo_url}" width="100" style="margin-bottom:8px;">
                        <div style="font-size:0.85rem; font-weight:600; color:#64748B;">Operated by {airline}</div>
                    </div>

                    <div class="visual-container">
                        <div style="text-align:right;">
                            <div class="time-big">{dep_time}</div>
                            <div class="city-code">{st.session_state.search_meta['origin']}</div>
                        </div>
                        
                        <div style="flex:1; text-align:center;">
                            <div style="font-size:0.8rem; font-weight:600; color:#64748B; margin-bottom:5px;">{dur_str}</div>
                            <div class="path-line">
                                <div class="plane-icon">✈️</div>
                            </div>
                            <div style="background:{stop_bg}; color:{stop_color}; padding:4px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; display:inline-block; margin-top:8px;">
                                {stop_label}
                            </div>
                        </div>

                        <div style="text-align:left;">
                            <div class="time-big">{arr_time}</div>
                            <div class="city-code">{st.session_state.search_meta['destination']}</div>
                        </div>
                    </div>

                    <div style="flex:1; text-align:right;">
                        {badge_html}
                        <div style="font-size:2.2rem; font-weight:800; color:#0F172A; letter-spacing:-1px;">{price:.0f}</div>
                        <div style="font-size:0.9rem; font-weight:600; color:#64748B;">{currency} per adult</div>
                    </div>
                </div>
                
                <div class="card-bottom">
                    <div style="display:flex; gap:20px;">
                        <span>🧳 Personal Item</span>
                        <span>🛡️ Secure Booking</span>
                    </div>
                    <div style="color:#0062E3; font-weight:700;">Flight Details &rarr;</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # --- SELECT BUTTON ---
        if st.button(f"Select Flight {idx}", key=f"btn_{idx}", use_container_width=True):
            st.session_state.shortlist.append({
                "airline": airline,
                "price": price,
                "curr": currency,
                "route": f"{st.session_state.search_meta['origin']} → {st.session_state.search_meta['destination']}"
            })
            st.rerun()

elif 'flights' in st.session_state:
    st.warning("No flights found. Try a different date.")
