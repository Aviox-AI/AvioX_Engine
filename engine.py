import streamlit as st
from amadeus import Client, ResponseError
from openai import OpenAI
import json
from datetime import datetime, timedelta

# --- 1. CONFIGURATION & SAFETY CHECKS ---
st.set_page_config(page_title="AvioX | Enterprise Travel", page_icon="✈️", layout="wide")

try:
    # Load secrets safely
    AMADEUS_KEY = st.secrets["AMADEUS_KEY"]
    AMADEUS_SECRET = st.secrets["AMADEUS_SECRET"]
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except Exception as e:
    st.error(f"❌ Critical Setup Error: Missing API Keys. Please check your secrets.toml file. ({e})")
    st.stop()

# Initialize Clients (Cached to prevent connection resets)
@st.cache_resource
def get_clients():
    amadeus = Client(client_id=AMADEUS_KEY, client_secret=AMADEUS_SECRET)
    ai = OpenAI(api_key=OPENAI_KEY)
    return amadeus, ai

amadeus, ai_client = get_clients()

# --- 2. PREMIUM CSS DESIGN SYSTEM ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    /* Global Polish */
    .stApp { background-color: #F8FAFC; font-family: 'Plus Jakarta Sans', sans-serif; }
    
    /* --- FLIGHT CARD (Apple-Style Design) --- */
    .flight-card {
        background: white;
        border-radius: 18px;
        border: 1px solid #EFF6FF;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        margin-bottom: 24px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        overflow: hidden;
    }
    .flight-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 30px -5px rgba(0, 98, 227, 0.15);
        border-color: #BFDBFE;
    }
    
    .card-main { padding: 28px 32px; display: flex; align-items: center; gap: 24px; }
    .card-footer { 
        background: #F8FAFC; 
        padding: 12px 32px; 
        border-top: 1px solid #EFF6FF;
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 600;
    }

    /* --- TYPOGRAPHY --- */
    .airport-code { font-size: 2.2rem; font-weight: 800; color: #1E293B; line-height: 1; }
    .city-name { font-size: 0.9rem; font-weight: 600; color: #94A3B8; margin-top: 4px; }
    .price-tag { font-size: 2.2rem; font-weight: 800; color: #0F172A; }
    .price-sub { font-size: 0.9rem; font-weight: 600; color: #64748B; }

    /* --- VISUAL TIMELINE --- */
    .timeline-container { flex: 1; text-align: center; position: relative; padding: 0 20px; }
    .duration-text { font-size: 0.85rem; color: #64748B; font-weight: 600; margin-bottom: 8px; }
    .flight-path { 
        height: 2px; 
        background: #E2E8F0; 
        width: 100%; 
        position: relative; 
        border-radius: 4px; 
    }
    .plane-icon {
        position: absolute;
        top: -10px;
        left: 50%;
        transform: translateX(-50%);
        background: white;
        padding: 0 6px;
        font-size: 1rem;
        color: #3B82F6;
    }
    
    /* --- BADGES --- */
    .badge-success { 
        background: #DCFCE7; color: #15803D; 
        padding: 4px 8px; border-radius: 6px; 
        font-size: 0.7rem; font-weight: 800; 
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    .badge-error { 
        background: #FEE2E2; color: #B91C1C; 
        padding: 4px 8px; border-radius: 6px; 
        font-size: 0.7rem; font-weight: 800; 
    }

    /* --- BUTTONS --- */
    /* Forces the Select button to fuse to the card bottom */
    div[data-testid="stVerticalBlock"] > div > div > div > div > button {
        border-radius: 0 0 18px 18px !important;
        margin-top: -24px !important;
        background-color: #2563EB !important;
        color: white !important;
        font-weight: 700 !important;
        height: 50px !important;
        border: none !important;
        z-index: 0;
    }
    div[data-testid="stVerticalBlock"] > div > div > div > div > button:hover {
        background-color: #1D4ED8 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR (TRIP WALLET) ---
with st.sidebar:
    st.markdown("### 🎒 Trip Wallet")
    
    # Initialize Session State for Shortlist
    if 'wallet' not in st.session_state:
        st.session_state.wallet = []

    # Display Saved Flights
    if st.session_state.wallet:
        for i, item in enumerate(st.session_state.wallet):
            st.markdown(f"""
                <div style="background:white; padding:12px; border-radius:10px; border:1px solid #E2E8F0; margin-bottom:8px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                    <div style="font-weight:700; color:#1E293B;">{item['airline']}</div>
                    <div style="font-size:0.8rem; color:#64748B;">{item['origin']} ➔ {item['dest']}</div>
                    <div style="color:#2563EB; font-weight:800; margin-top:4px;">{item['price']} {item['curr']}</div>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("Clear Wallet", use_container_width=True):
            st.session_state.wallet = []
            st.rerun()
    else:
        st.info("Your wallet is empty. Search and select a flight to pin it here.")

# --- 4. HEADER & SEARCH BAR ---
# Perfect Alignment Grid
c1, c2, c3 = st.columns([1.5, 5, 1.2])

with c1:
    st.markdown("""
        <h1 style='color: #2563EB; margin: 0; padding-top: 8px; font-size: 2.8rem; font-weight: 900; letter-spacing: -2px; line-height: 1;'>
            Avio<span style='color: #1E293B;'>X</span>
        </h1>
    """, unsafe_allow_html=True)

with c2:
    # Adding vertical padding to align input with logo
    st.markdown("<div style='padding-top: 8px;'>", unsafe_allow_html=True)
    user_query = st.text_input("", placeholder="Try 'London to Dubai in October'", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

with c3:
    st.markdown("<div style='padding-top: 8px;'>", unsafe_allow_html=True)
    search_pressed = st.button("Search", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 40px;'></div>", unsafe_allow_html=True)

# --- 5. SEARCH LOGIC ENGINE ---
if user_query and search_pressed:
    with st.spinner("Connecting to global reservation systems..."):
        try:
            # 1. AI Parsing (Strict JSON Mode)
            today = datetime.now().strftime("%Y-%m-%d")
            prompt = f"""
            You are a flight engine API. 
            User Query: "{user_query}"
            Task: Extract Origin (IATA), Destination (IATA), and Date (YYYY-MM-DD).
            Rules:
            - If date is missing/past, use '2026-10-15' (Future Safe Date).
            - Return raw JSON only.
            Example: {{"origin": "LHR", "destination": "JFK", "date": "2026-10-15"}}
            """
            
            ai_res = ai_client.chat.completions.create(
                model="gpt-3.5-turbo", 
                messages=[{"role": "user", "content": prompt}], 
                temperature=0
            )
            
            # 2. JSON Sanitizer (Prevents crashes)
            raw_content = ai_res.choices[0].message.content
            clean_json = raw_content.replace('```json', '').replace('```', '').strip()
            search_params = json.loads(clean_json)
            
            # Store metadata for display
            st.session_state.search_meta = search_params
            
            # 3. Amadeus API Call (Error Handled)
            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode=search_params['origin'].upper(),
                destinationLocationCode=search_params['destination'].upper(),
                departureDate=search_params['date'],
                adults=1,
                max=10
            )
            
            st.session_state.flights = response.data
            
        except ResponseError as error:
            st.error(f"⚠️ Amadeus API Error: {error.response.result['errors'][0]['detail']}")
        except Exception as e:
            st.error(f"⚠️ System Error: {e}")

# --- 6. RESULTS RENDERER ---
if 'flights' in st.session_state and st.session_state.flights:
    
    # Sort by Cheapest Default
    flights = sorted(st.session_state.flights, key=lambda x: float(x['price']['total']))
    min_price = float(flights[0]['price']['total'])
    
    # Iterate and Display
    for idx, flight in enumerate(flights):
        
        # --- DATA PREP (Pure Python) ---
        price = float(flight['price']['total'])
        currency = flight['price']['currency']
        airline_code = flight['validatingAirlineCodes'][0]
        itinerary = flight['itineraries'][0]
        segments = itinerary['segments']
        
        dep_iata = segments[0]['departure']['iataCode']
        arr_iata = segments[-1]['arrival']['iataCode']
        dep_time = segments[0]['departure']['at'][11:16]
        arr_time = segments[-1]['arrival']['at'][11:16]
        
        # Duration Cleaning
        dur_raw = itinerary['duration'][2:].lower() # PT12H -> 12h
        duration = dur_raw.replace('h', 'h ').replace('m', 'm')
        
        stops = len(segments) - 1
        stop_badge = f"<span class='badge-success'>DIRECT</span>" if stops == 0 else f"<span class='badge-error'>{stops} STOP</span>"
        best_price_badge = f"<div class='badge-success' style='margin-bottom:5px; display:inline-block;'>BEST PRICE</div>" if price == min_price else ""

        # Airline Logo URL
        logo_url = f"https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline_code}.svg"

        # --- HTML INJECTION ---
        st.markdown(f"""
            <div class="flight-card">
                <div class="card-main">
                    <div style="width: 120px;">
                        <img src="{logo_url}" width="100" onerror="this.style.display='none'">
                        <div style="font-size:0.8rem; font-weight:700; color:#64748B; margin-top:5px;">{airline_code}</div>
                    </div>

                    <div style="text-align:right; min-width:80px;">
                        <div class="airport-code">{dep_time}</div>
                        <div class="city-name">{dep_iata}</div>
                    </div>

                    <div class="timeline-container">
                        <div class="duration-text">{duration}</div>
                        <div class="flight-path">
                            <div class="plane-icon">✈</div>
                        </div>
                        <div style="margin-top:8px;">{stop_badge}</div>
                    </div>

                    <div style="text-align:left; min-width:80px;">
                        <div class="airport-code">{arr_time}</div>
                        <div class="city-name">{arr_iata}</div>
                    </div>

                    <div style="text-align:right; min-width:140px;">
                        {best_price_badge}
                        <div class="price-tag">{price:.0f}</div>
                        <div class="price-sub">{currency}</div>
                    </div>
                </div>
                
                <div class="card-footer">
                    <div style="display:flex; gap:20px;">
                        <span>🧳 Personal Item Included</span>
                        <span>♻️ Eco-Certified</span>
                    </div>
                    <div style="color:#2563EB; font-weight:700;">View Flight Details &rarr;</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # --- SELECT BUTTON ---
        # The key uses the index to be unique
        if st.button(f"Select Flight {idx}", key=f"btn_{idx}", use_container_width=True):
            # Add to Wallet
            st.session_state.wallet.append({
                "airline": airline_code,
                "origin": dep_iata,
                "dest": arr_iata,
                "price": price,
                "curr": currency
            })
            st.rerun()

elif 'flights' in st.session_state:
    st.warning("No flights found. Try a major route (e.g. LHR to JFK) for a future date (e.g. Oct 2026).")
