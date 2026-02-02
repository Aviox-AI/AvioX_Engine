import streamlit as st
from amadeus import Client, ResponseError
from openai import OpenAI
import json
import re
import textwrap  # <--- THIS IS THE KEY FIX
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="AvioX | Elite Travel", page_icon="✈️", layout="wide")

try:
    AMADEUS_KEY = st.secrets["AMADEUS_KEY"]
    AMADEUS_SECRET = st.secrets["AMADEUS_SECRET"]
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except Exception as e:
    st.error(f"❌ API Key Error: {e}")
    st.stop()

@st.cache_resource
def get_clients():
    return Client(client_id=AMADEUS_KEY, client_secret=AMADEUS_SECRET), OpenAI(api_key=OPENAI_KEY)

amadeus, ai_client = get_clients()

# --- 2. CSS STYLING ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    .stApp { background-color: #F8FAFC; font-family: 'Plus Jakarta Sans', sans-serif; }

    /* SEARCH BAR ALIGNMENT */
    [data-testid="column"] {
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
    }

    /* Input Styling */
    .stTextInput input {
        min-height: 55px;
        padding: 12px 15px;
        font-size: 1.1rem;
        border-radius: 12px;
        border: 2px solid #E2E8F0;
    }
    .stTextInput input:focus { border-color: #0062E3; }

    /* Button Styling */
    .stButton button {
        min-height: 55px;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        background-color: #0062E3 !important;
        color: white !important;
        border: none !important;
        width: 100%;
    }
    .stButton button:hover { background-color: #004FB8 !important; }

    /* FLIGHT CARD */
    .flight-card {
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.03);
        border: 1px solid #EFF6FF;
        margin-bottom: 24px;
        transition: transform 0.2s;
    }
    .flight-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 25px rgba(0, 98, 227, 0.1);
        border-color: #BFDBFE;
    }
    
    .card-content { padding: 30px; display: flex; align-items: center; gap: 20px; }
    
    .card-footer {
        background: #F8FAFC;
        padding: 12px 30px;
        border-top: 1px solid #EFF6FF;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 0 0 16px 16px;
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 600;
    }

    /* TYPOGRAPHY */
    .airport-code { font-size: 1.8rem; font-weight: 800; color: #0F172A; line-height: 1; }
    .city-label { font-size: 0.9rem; font-weight: 700; color: #94A3B8; margin-top: 4px; }
    
    /* TIMELINE */
    .timeline-track {
        flex: 1;
        height: 2px;
        background: #E2E8F0;
        position: relative;
        margin: 10px 20px;
    }
    .plane-dot {
        position: absolute;
        top: -12px;
        left: 50%;
        transform: translateX(-50%);
        background: white;
        padding: 0 6px;
        font-size: 1.2rem;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. HELPER FUNCTIONS ---
def get_clean_json(raw_text):
    try:
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        return json.loads(match.group()) if match else None
    except:
        return None

# --- 4. SIDEBAR ---
with st.sidebar:
    st.header("🎒 Trip Wallet")
    if 'wallet' not in st.session_state: st.session_state.wallet = []

    if st.session_state.wallet:
        for item in st.session_state.wallet:
            st.success(f"✈️ {item['airline']} • {item['price']} {item['curr']}")
        if st.button("Clear Wallet"):
            st.session_state.wallet = []
            st.rerun()
    else:
        st.info("Your saved flights appear here.")

# --- 5. ALIGNED HEADER ---
c1, c2, c3 = st.columns([1.5, 5, 1.5])

with c1:
    st.markdown("<h1 style='color:#0062E3; margin:0; font-size:2.5rem; font-weight:900;'>AvioX</h1>", unsafe_allow_html=True)

with c2:
    query = st.text_input("", placeholder="e.g. London to NYC in October", label_visibility="collapsed")

with c3:
    search_btn = st.button("Search Flights", use_container_width=True)

st.markdown("---")

# --- 6. LOGIC ENGINE ---
if query and search_btn:
    with st.spinner("Analyzing flight paths..."):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            prompt = f"""
            Extract entities from: "{query}".
            Return valid JSON only: {{"origin": "IATA_CODE", "destination": "IATA_CODE", "date": "YYYY-MM-DD"}}
            Rules: If date missing, use '2026-10-20'. Origin/Dest must be IATA.
            """
            
            ai_res = ai_client.chat.completions.create(
                model="gpt-3.5-turbo", 
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            
            meta = get_clean_json(ai_res.choices[0].message.content)
            
            if not meta:
                st.error("Could not understand location. Try 'London to Paris'.")
                st.stop()

            st.session_state.meta = meta

            # Amadeus API
            resp = amadeus.shopping.flight_offers_search.get(
                originLocationCode=meta['origin'].upper(),
                destinationLocationCode=meta['destination'].upper(),
                departureDate=meta['date'],
                adults=1, max=10
            )
            st.session_state.flights = resp.data

        except ResponseError as e:
            st.error(f"API Error: {e.response.result['errors'][0]['detail']}")
        except Exception as e:
            st.error(f"System Error: {e}")

# --- 7. RESULTS RENDERER ---
if 'flights' in st.session_state and st.session_state.flights:
    
    # Sort Data
    flights = sorted(st.session_state.flights, key=lambda x: float(x['price']['total']))
    min_price = float(flights[0]['price']['total'])

    for idx, flight in enumerate(flights):
        # 1. PREPARE VARIABLES
        price = float(flight['price']['total'])
        currency = flight['price']['currency']
        airline = flight['validatingAirlineCodes'][0]
        it = flight['itineraries'][0]
        segs = it['segments']
        
        dep_code = segs[0]['departure']['iataCode']
        arr_code = segs[-1]['arrival']['iataCode']
        dep_time = segs[0]['departure']['at'][11:16]
        arr_time = segs[-1]['arrival']['at'][11:16]
        
        dur_raw = it['duration'][2:].lower()
        duration = dur_raw.replace('h', 'h ').replace('m', 'm')
        
        stops = len(segs) - 1
        
        # 2. GENERATE BADGE STRINGS
        if stops == 0:
            badge_html = "<span style='background:#DCFCE7; color:#166534; padding:4px 8px; border-radius:4px; font-weight:700; font-size:0.75rem;'>DIRECT</span>"
        else:
            badge_html = f"<span style='background:#FEE2E2; color:#991B1B; padding:4px 8px; border-radius:4px; font-weight:700; font-size:0.75rem;'>{stops} STOP</span>"
            
        best_price_html = ""
        if price == min_price:
            best_price_html = "<div style='background:#ECFDF5; color:#059669; border:1px solid #A7F3D0; padding:4px 8px; border-radius:6px; font-size:0.7rem; font-weight:800; display:inline-block; margin-bottom:5px;'>BEST PRICE</div>"

        logo_url = f"https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline}.svg"

        # 3. HTML GENERATION (With dedent to fix the raw html bug)
        card_html = textwrap.dedent(f"""
        <div class="flight-card">
            <div class="card-content">
                <div style="flex:1;">
                    <img src="{logo_url}" width="100" style="margin-bottom:8px;" onerror="this.style.display='none'">
                    <div style="font-size:0.8rem; font-weight:600; color:#64748B;">Operated by {airline}</div>
                </div>
                <div style="text-align:right;">
                    <div class="airport-code">{dep_time}</div>
                    <div class="city-label">{dep_code}</div>
                </div>
                <div style="flex:2; text-align:center; padding:0 20px;">
                    <div style="font-size:0.85rem; font-weight:600; color:#64748B; margin-bottom:5px;">{duration}</div>
                    <div class="timeline-track">
                        <div class="plane-dot">✈️</div>
                    </div>
                    <div style="margin-top:8px;">{badge_html}</div>
                </div>
                <div style="text-align:left;">
                    <div class="airport-code">{arr_time}</div>
                    <div class="city-label">{arr_code}</div>
                </div>
                <div style="flex:1; text-align:right;">
                    {best_price_html}
                    <div style="font-size:2.2rem; font-weight:800; color:#0F172A; letter-spacing:-1px;">{price:.0f}</div>
                    <div style="font-size:0.9rem; font-weight:600; color:#64748B;">{currency}</div>
                </div>
            </div>
            <div class="card-footer">
                <div>🛍️ <b>Personal Item</b> included &nbsp;&bull;&nbsp; 🛡️ <b>Secure</b> Booking</div>
                <div style="color:#0062E3; font-weight:700;">Flight Details &rarr;</div>
            </div>
        </div>
        """)

        # 4. RENDER WITH DEDENT
        st.markdown(card_html, unsafe_allow_html=True)
        
        if st.button(f"Select Flight {idx}", key=f"btn_{idx}", use_container_width=True):
            st.session_state.wallet.append({"airline": airline, "price": price, "curr": currency})
            st.toast("Added to Wallet!")
            st.rerun()

elif 'flights' in st.session_state:
    st.info("No flights found. Try a major route like LHR to JFK.")
