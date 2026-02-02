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

# --- 2. THE "SUPREME" DESIGN SYSTEM ---
st.set_page_config(page_title="AvioX | Next-Gen Travel", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    /* GLOBAL RESET */
    .stApp { background-color: #F3F5F9; font-family: 'Plus Jakarta Sans', sans-serif; }
    h1, h2, h3, p, div, span, button { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    /* --- NAVBAR --- */
    .nav-container {
        display: flex;
        align-items: center;
        gap: 20px;
        padding-bottom: 25px;
        border-bottom: 1px solid #E2E8F0;
        margin-bottom: 35px;
    }
    
    /* --- FLIGHT CARD (The Star of the Show) --- */
    .flight-card {
        background: white;
        border-radius: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
        border: 1px solid #EFF2F6;
        margin-bottom: 24px;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
    }
    .flight-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px rgba(0,98,227,0.12);
        border-color: #0062E3;
    }
    
    .card-main { padding: 32px; display: flex; align-items: center; }
    
    .card-sub {
        background: #F8FAFC;
        padding: 14px 32px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-top: 1px solid #EFF2F6;
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 600;
    }

    /* --- TIMELINE VISUALIZER --- */
    .route-visual {
        flex: 3;
        display: flex;
        align-items: center;
        gap: 30px;
        margin: 0 40px;
        position: relative;
    }
    .time-group { text-align: center; min-width: 80px; }
    .time-large { font-size: 1.8rem; font-weight: 800; color: #1E293B; line-height: 1.1; }
    .iata-code { font-size: 1.1rem; color: #94A3B8; font-weight: 700; margin-top: 4px; }
    
    .duration-line {
        flex: 1;
        text-align: center;
        position: relative;
    }
    .line-bar {
        height: 2px;
        background: #E2E8F0;
        width: 100%;
        margin: 8px 0;
        border-radius: 2px;
        position: relative;
    }
    .plane-dot {
        position: absolute;
        top: -8px;
        left: 50%;
        transform: translateX(-50%);
        background: white;
        padding: 0 6px;
        font-size: 1rem;
    }

    /* --- PRICE TAGS --- */
    .price-block { text-align: right; min-width: 140px; }
    .price-big { font-size: 2.2rem; font-weight: 800; color: #0F172A; letter-spacing: -1px; }
    .price-curr { font-size: 1rem; color: #64748B; font-weight: 600; }
    
    .badge-best {
        background: linear-gradient(135deg, #059669 0%, #10B981 100%);
        color: white;
        padding: 5px 10px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 800;
        text-transform: uppercase;
        display: inline-block;
        margin-bottom: 5px;
        box-shadow: 0 2px 6px rgba(16,185,129,0.2);
    }

    /* --- BUTTONS & INPUTS --- */
    .stTextInput input {
        height: 60px;
        border-radius: 12px;
        border: 2px solid #E2E8F0;
        font-size: 1.1rem;
        padding-left: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.02);
    }
    .stTextInput input:focus { border-color: #0062E3; }
    
    .stButton button {
        height: 60px;
        border-radius: 12px;
        background: #0062E3;
        color: white;
        font-weight: 700;
        font-size: 1.1rem;
        border: none;
        transition: 0.2s;
    }
    .stButton button:hover { background: #0051C0; transform: scale(1.01); }
    
    /* Fix Select Button to attach to card */
    div[data-testid="stVerticalBlock"] > div > button {
        border-radius: 0 0 20px 20px;
        margin-top: -24px;
        z-index: 1;
        height: 50px;
        font-size: 1rem;
        background: #0062E3;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR (TRIP PLANNER) ---
with st.sidebar:
    st.markdown("### ✈️ Trip Planner")
    st.markdown("Saved flights appear here.")
    
    if 'shortlist' not in st.session_state: st.session_state.shortlist = []

    if st.session_state.shortlist:
        for item in st.session_state.shortlist:
            st.markdown(f"""
                <div style="background: white; padding: 16px; border-radius: 12px; border: 1px solid #E2E8F0; margin-bottom: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
                    <div style="font-weight: 700; color: #1E293B; font-size: 1rem;">{item['airline']}</div>
                    <div style="font-size: 0.85rem; color: #64748B; margin-top: 2px;">{item['route']}</div>
                    <div style="font-size: 1.2rem; font-weight: 800; color: #0062E3; margin-top: 8px;">{item['price']} {item['curr']}</div>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("Clear Planner", type="secondary"):
            st.session_state.shortlist = []
            st.rerun()
    else:
        st.info("Your planner is empty. Search and select a flight to save it.")

# --- 4. HEADER & SEARCH ---
c1, c2, c3 = st.columns([1.5, 4.5, 1.2], gap="large")

with c1:
    st.markdown("""
        <h1 style='color: #0062E3; margin: 0; padding-top: 8px; font-size: 3.2rem; font-weight: 900; letter-spacing: -2px; line-height: 1;'>
            Avio<span style='color: #1E293B;'>X</span>
        </h1>
    """, unsafe_allow_html=True)

with c2:
    user_query = st.text_input("", placeholder="Where to? (e.g., NYC to London in October)", label_visibility="collapsed")

with c3:
    search_pressed = st.button("Search", use_container_width=True)

st.markdown("<div style='margin-bottom: 40px;'></div>", unsafe_allow_html=True)

# --- 5. LOGIC ENGINE ---
if user_query and search_pressed:
    with st.spinner("Analyzing global flight network..."):
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            prompt = f"""
            Extract flight data from: '{user_query}'.
            Return JSON: {{"origin": "IATA_CODE", "destination": "IATA_CODE", "date": "YYYY-MM-DD"}}
            Context: Today is {today}.
            """
            ai_res = ai_client.chat.completions.create(
                model="gpt-3.5-turbo", 
                messages=[{"role": "user", "content": prompt}], 
                temperature=0
            )
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
            st.error(f"Search failed: {e}")

# --- 6. RESULTS RENDERING ---
if 'flights' in st.session_state and st.session_state.flights:
    
    # Sort Logic
    df = st.session_state.flights
    df = sorted(df, key=lambda x: float(x['price']['total']))
    min_price = float(df[0]['price']['total'])

    # Display Loop
    for idx, flight in enumerate(df):
        
        # --- PYTHON LOGIC (Calculated BEFORE HTML) ---
        # 1. Price Data
        price_val = float(flight['price']['total'])
        currency = flight['price']['currency']
        
        # 2. Airline Data
        airline_code = flight['validatingAirlineCodes'][0]
        airline_logo = f"https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline_code}.svg"
        
        # 3. Time Data
        itinerary = flight['itineraries'][0]
        segments = itinerary['segments']
        dep_time = segments[0]['departure']['at'][11:16]
        arr_time = segments[-1]['arrival']['at'][11:16]
        
        # 4. Duration & Stops
        raw_dur = itinerary['duration'][2:].lower()
        duration_str = raw_dur.replace('h', 'h ').replace('m', 'm')
        stops = len(segments) - 1
        
        # 5. Visual Logic (Colors & Text)
        if stops == 0:
            stop_text = "Direct Flight"
            stop_color = "#059669" # Green
            stop_bg = "#ECFDF5"
        else:
            stop_text = f"{stops} Stop(s)"
            stop_color = "#EF4444" # Red
            stop_bg = "#FEF2F2"

        # 6. Badge Logic
        badge_html = ""
        if price_val == min_price:
            badge_html = '<div class="badge-best">BEST PRICE</div>'

        # --- HTML INJECTION ---
        st.markdown(f"""
            <div class="flight-card">
                <div class="card-main">
                    <div style="flex: 1;">
                        <img src="{airline_logo}" width="100" style="margin-bottom: 10px; display: block;" onerror="this.style.display='none'">
                        <div style="font-weight: 700; color: #475569; font-size: 0.9rem;">{airline_code} Airlines</div>
                    </div>

                    <div class="route-visual">
                        <div class="time-group">
                            <div class="time-large">{dep_time}</div>
                            <div class="iata-code">{st.session_state.search_meta['origin']}</div>
                        </div>
                        
                        <div class="duration-line">
                            <div style="font-size: 0.85rem; color: #64748B; font-weight: 600; margin-bottom: 5px;">{duration_str}</div>
                            <div class="line-bar">
                                <div class="plane-dot">✈️</div>
                            </div>
                            <div style="display: inline-block; background: {stop_bg}; color: {stop_color}; padding: 4px 10px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; margin-top: 5px;">
                                {stop_text}
                            </div>
                        </div>

                        <div class="time-group">
                            <div class="time-large">{arr_time}</div>
                            <div class="iata-code">{st.session_state.search_meta['destination']}</div>
                        </div>
                    </div>

                    <div class="price-block">
                        {badge_html}
                        <div class="price-big">{price_val:.0f}</div>
                        <div class="price-curr">{currency} per adult</div>
                    </div>
                </div>
                
                <div class="card-sub">
                    <div style="display: flex; gap: 24px;">
                        <span>🧳 <b>Personal Item</b> included</span>
                        <span>🛡️ <b>Secure</b> booking</span>
                        <span style="color: #059669;">🌿 <b>-15% CO2</b> emission</span>
                    </div>
                    <div style="color: #0062E3; font-weight: 700; cursor: pointer;">Flight Details &rarr;</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # --- ACTION BUTTON ---
        if st.button(f"Select Flight {idx}", key=f"btn_{idx}", use_container_width=True):
            st.session_state.shortlist.append({
                "airline": airline_code,
                "price": price_val,
                "curr": currency,
                "route": f"{st.session_state.search_meta['origin']} → {st.session_state.search_meta['destination']}"
            })
            st.rerun()

elif 'flights' in st.session_state:
    st.info("No flights found for this route. Try a major hub like LHR, JFK, or DXB.")
