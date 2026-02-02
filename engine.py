import streamlit as st
from amadeus import Client, ResponseError
from openai import OpenAI
import json
from datetime import datetime

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="AvioX", page_icon="✈️", layout="wide")

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

# --- 2. CSS STYLING (THE FIX) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
    
    .stApp { background-color: #F8FAFC; font-family: 'Plus Jakarta Sans', sans-serif; }

    /* --- SEARCH BAR ALIGNMENT FIX --- */
    /* This aligns the text input and button perfectly horizontally */
    div[data-testid="column"] {
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
    }
    
    /* Input Box Styling */
    .stTextInput input {
        height: 55px;
        border-radius: 10px;
        border: 1px solid #E2E8F0;
        padding-left: 20px;
    }

    /* Button Styling */
    .stButton button {
        height: 55px;
        border-radius: 10px;
        background-color: #0062E3;
        color: white;
        font-weight: 700;
        border: none;
        width: 100%;
    }
    .stButton button:hover { background-color: #004FB8; }

    /* --- FLIGHT CARD CONTAINER --- */
    .flight-card {
        background: white;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #EFF6FF;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .flight-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 15px -3px rgba(0, 98, 227, 0.1);
        border-color: #93C5FD;
    }
    
    .card-content { padding: 25px 35px; display: flex; align-items: center; justify-content: space-between; }
    
    .card-footer {
        background: #F8FAFC;
        padding: 12px 35px;
        border-top: 1px solid #F1F5F9;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-radius: 0 0 16px 16px;
        font-size: 0.85rem;
        color: #64748B;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. SIDEBAR (WALLET) ---
with st.sidebar:
    st.header("🎒 Trip Wallet")
    if 'wallet' not in st.session_state: st.session_state.wallet = []
    
    if st.session_state.wallet:
        for item in st.session_state.wallet:
            st.success(f"✈️ {item['airline']}: {item['price']} {item['curr']}")
        if st.button("Clear Wallet"):
            st.session_state.wallet = []
            st.rerun()
    else:
        st.info("Saved flights appear here.")

# --- 4. HEADER & SEARCH ---
c1, c2, c3 = st.columns([1.5, 5, 1.2])

with c1:
    st.markdown("<h1 style='color:#0062E3; margin:0; padding-top:10px; font-weight:800;'>AvioX</h1>", unsafe_allow_html=True)

with c2:
    query = st.text_input("", placeholder="e.g. London to NYC in October", label_visibility="collapsed")

with c3:
    search = st.button("Search Flights")

# --- 5. LOGIC ENGINE ---
if query and search:
    try:
        with st.spinner("Finding best routes..."):
            # 1. AI Parsing
            today = datetime.now().strftime("%Y-%m-%d")
            prompt = f"Extract JSON: {{'origin': 'IATA', 'destination': 'IATA', 'date': 'YYYY-MM-DD'}} from '{query}'. If date missing, use '2026-10-20'. Return ONLY JSON."
            
            ai_res = ai_client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
            clean_json = ai_res.choices[0].message.content.replace('```json', '').replace('```', '').strip()
            meta = json.loads(clean_json)
            st.session_state.meta = meta

            # 2. Amadeus API
            resp = amadeus.shopping.flight_offers_search.get(
                originLocationCode=meta['origin'].upper(),
                destinationLocationCode=meta['destination'].upper(),
                departureDate=meta['date'],
                adults=1, max=10
            )
            st.session_state.flights = resp.data

    except Exception as e:
        st.error(f"Search Error: {e}")

# --- 6. RESULTS RENDERER (STRICT HTML) ---
if 'flights' in st.session_state and st.session_state.flights:
    
    # Sort by Price
    flights = sorted(st.session_state.flights, key=lambda x: float(x['price']['total']))
    min_price = float(flights[0]['price']['total'])

    for idx, flight in enumerate(flights):
        # Extract Data
        price = float(flight['price']['total'])
        currency = flight['price']['currency']
        airline = flight['validatingAirlineCodes'][0]
        it = flight['itineraries'][0]
        segments = it['segments']
        
        dep_code = segments[0]['departure']['iataCode']
        arr_code = segments[-1]['arrival']['iataCode']
        dep_time = segments[0]['departure']['at'][11:16]
        arr_time = segments[-1]['arrival']['at'][11:16]
        
        # Format Duration
        dur_raw = it['duration'][2:].lower()
        duration = dur_raw.replace('h', 'h ').replace('m', 'm')
        
        # Badge Logic
        stops = len(segments) - 1
        stop_badge = f"<span style='color:#166534; background:#DCFCE7; padding:4px 8px; border-radius:4px; font-weight:700; font-size:0.75rem;'>DIRECT</span>" if stops == 0 else f"<span style='color:#991B1B; background:#FEE2E2; padding:4px 8px; border-radius:4px; font-weight:700; font-size:0.75rem;'>{stops} STOP</span>"
        price_badge = f"<div style='color:#15803D; background:#DCFCE7; border:1px solid #86EFAC; padding:2px 8px; border-radius:4px; font-weight:800; font-size:0.7rem; display:inline-block; margin-bottom:4px;'>BEST PRICE</div>" if price == min_price else ""
        
        logo = f"https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline}.svg"

        # --- THE HTML BLOCK ---
        html_code = f"""
        <div class="flight-card">
            <div class="card-content">
                <div style="width:120px;">
                    <img src="{logo}" width="100" style="margin-bottom:5px;">
                    <div style="font-size:0.8rem; font-weight:600; color:#64748B;">{airline}</div>
                </div>

                <div style="text-align:right;">
                    <div style="font-size:1.8rem; font-weight:800; color:#0F172A; line-height:1;">{dep_time}</div>
                    <div style="font-size:1rem; font-weight:700; color:#94A3B8;">{dep_code}</div>
                </div>

                <div style="flex:1; padding:0 30px; text-align:center;">
                    <div style="font-size:0.85rem; font-weight:600; color:#64748B; margin-bottom:5px;">{duration}</div>
                    <div style="height:2px; background:#E2E8F0; position:relative; width:100%;">
                        <div style="position:absolute; top:-10px; left:50%; transform:translateX(-50%); background:white; padding:0 5px;">✈️</div>
                    </div>
                    <div style="margin-top:8px;">{stop_badge}</div>
                </div>

                <div style="text-align:left;">
                    <div style="font-size:1.8rem; font-weight:800; color:#0F172A; line-height:1;">{arr_time}</div>
                    <div style="font-size:1rem; font-weight:700; color:#94A3B8;">{arr_code}</div>
                </div>

                <div style="text-align:right; width:140px;">
                    {price_badge}
                    <div style="font-size:2.2rem; font-weight:800; color:#0F172A; letter-spacing:-1px;">{price:.0f}</div>
                    <div style="font-size:0.9rem; font-weight:600; color:#64748B;">{currency}</div>
                </div>
            </div>
            
            <div class="card-footer">
                <div>🛍️ <b>Personal Item</b> included &nbsp;&nbsp; • &nbsp;&nbsp; 🛡️ <b>Secure</b> Booking</div>
                <div style="color:#0062E3; font-weight:700;">Flight Details &rarr;</div>
            </div>
        </div>
        """
        
        # RENDER THE HTML
        st.markdown(html_code, unsafe_allow_html=True)
        
        # SELECT BUTTON
        if st.button(f"Select Flight {idx}", key=f"btn_{idx}", use_container_width=True):
            st.session_state.wallet.append({"airline": airline, "price": price, "curr": currency})
            st.rerun()
