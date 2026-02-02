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

@st.cache_resource
def get_clients():
    return Client(client_id=AMADEUS_KEY, client_secret=AMADEUS_SECRET), OpenAI(api_key=OPENAI_KEY)

amadeus, ai_client = get_clients()

# --- 2. PAGE CONFIG & THEME ---
st.set_page_config(page_title="AvioX AI", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    .stApp { background-color: #F1F2F8; }
    
    /* Integrated Flight Card */
    .flight-card {
        background: white;
        border-radius: 12px 12px 0 0; /* Rounded top only */
        box-shadow: 0 1px 4px rgba(37,32,31,.1);
        color: #25201F;
        border: 1px solid #E1E2E9;
        margin-bottom: 0px;
    }
    
    .card-body { padding: 24px 32px; display: flex; align-items: center; }
    
    .card-footer {
        background: #F9FAFB;
        border-top: 1px solid #E1E2E9;
        padding: 10px 32px;
        display: flex;
        justify-content: space-between;
        font-size: 0.8rem;
        color: #68697F;
    }

    /* Price Insight Badges */
    .badge {
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: 800;
        font-size: 0.7rem;
        text-transform: uppercase;
        margin-bottom: 8px;
        display: inline-block;
    }
    .badge-cheapest { background: #E2F5F3; color: #00A698; border: 1px solid #00A698; }
    .badge-fastest { background: #F0F4FF; color: #0062E3; border: 1px solid #0062E3; }

    /* The Integrated Button */
    .stButton>button {
        background-color: #0062E3 !important;
        color: white !important;
        border-radius: 0 0 12px 12px !important;
        height: 50px !important;
        border: none !important;
        font-weight: 700 !important;
        margin-top: -1px !important; /* Fuse button to card */
        transition: 0.2s;
    }
    .stButton>button:hover { background-color: #004FB8 !important; transform: scale(1.005); }

    .route-visual {
        flex: 3;
        display: flex;
        align-items: center;
        gap: 30px;
        margin: 0 40px;
        padding: 0 20px;
        border-left: 1px solid #F1F2F8;
        border-right: 1px solid #F1F2F8;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SIDEBAR (Comparison Tool) ---
with st.sidebar:
    st.markdown("### 📋 Shortlist")
    if 'shortlist' not in st.session_state or not st.session_state.shortlist:
        st.info("No flights selected yet. Click a flight to compare.")
    else:
        for item in st.session_state.shortlist:
            st.success(f"✈️ {item['airline']} - {item['price']} {item['curr']}")
        if st.button("Clear Shortlist"):
            st.session_state.shortlist = []
            st.rerun()

# --- 4. NAVIGATION BAR ---
n1, n2, n3 = st.columns([2, 5, 1.2])
with n1:
    st.markdown("<h1 style='color: #0062E3; margin: 0; font-size: 3.5rem; font-weight: 900; letter-spacing: -3px;'>Avio<span style='color: #25201F;'>X</span></h1>", unsafe_allow_html=True)
with n2:
    st.markdown("<div style='padding-top: 15px;'>", unsafe_allow_html=True)
    user_query = st.text_input("", placeholder="Where to? (e.g. London to Paris in October)", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
with n3:
    st.markdown("<div style='padding-top: 15px;'>", unsafe_allow_html=True)
    search_btn = st.button("Search", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# --- 5. LOGIC ---
if user_query and search_btn:
    with st.spinner("AvioX AI is crunching global routes..."):
        try:
            # AI Data Parsing
            sim_date = datetime.now().strftime("%Y-%m-%d")
            prompt = f"Convert to JSON: '{user_query}'. Return ONLY JSON: {{\"origin\": \"IATA\", \"destination\": \"IATA\", \"date\": \"YYYY-MM-DD\"}}. Ref: Today is {sim_date}."
            ai_res = ai_client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0)
            clean_json = ai_res.choices[0].message.content.strip().replace('```json', '').replace('```', '')
            st.session_state.search_meta = json.loads(clean_json)
            
            # Amadeus Call
            resp = amadeus.shopping.flight_offers_search.get(
                originLocationCode=st.session_state.search_meta['origin'].upper(),
                destinationLocationCode=st.session_state.search_meta['destination'].upper(),
                departureDate=st.session_state.search_meta['date'],
                adults=1, max=25
            )
            st.session_state.flights = resp.data
        except Exception as e:
            st.error(f"Connection Error: {e}")

# --- 6. DISPLAY RESULTS ---
if 'flights' in st.session_state:
    f1, f2, f3 = st.columns([1, 1, 3])
    with f1: sort_opt = st.selectbox("Sort", ["Cheapest", "Fastest"])
    with f2: stop_opt = st.selectbox("Stops", ["All", "Direct Only"])
    with f3: st.markdown(f"<p style='text-align:right; padding-top:35px;'>Results for <b>{st.session_state.search_meta['origin']} → {st.session_state.search_meta['destination']}</b></p>", unsafe_allow_html=True)

    # Filtering Logic
    df = st.session_state.flights
    if stop_opt == "Direct Only":
        df = [f for f in df if len(f['itineraries'][0]['segments']) == 1]
    
    # Identify highlights
    min_price = min([float(f['price']['total']) for f in df]) if df else 0
    
    [Image of a flight search results page with comparison features and price badges]

    for idx, flight in enumerate(df):
        price = float(flight['price']['total'])
        curr = flight['price']['currency']
        airline = flight['validatingAirlineCodes'][0]
        it = flight['itineraries'][0]
        dur_raw = it['duration'] # e.g. PT14H30M
        dep = it['segments'][0]['departure']['at'][11:16]
        arr = it['segments'][-1]['arrival']['at'][11:16]
        dur_clean = dur_raw[2:].lower().replace('h', 'h ').replace('m', 'm')
        stops = len(it['segments']) - 1

        st.markdown(f"""
            <div class="flight-card">
                <div class="card-body">
                    <div style="flex: 1;">
                        <img src="https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline.upper()}.svg" width="110">
                        <div style="font-size: 0.75rem; color: #68697F; font-weight: 700; margin-top: 5px;">{airline}</div>
                    </div>

                    <div class="route-visual">
                        <div style="text-align: right;">
                            <div style="font-size: 1.6rem; font-weight: 800;">{dep}</div>
                            <div style="color: #68697F; font-size: 1rem; font-weight: 700;">{st.session_state.search_meta['origin']}</div>
                        </div>
                        <div style="text-align: center; flex: 1;">
                            <div style="font-size: 0.8rem; color: #68697F; font-weight: 600;">{dur_clean}</div>
                            <div style="position: relative; height: 2px; background: #E1E2E9; width: 100%; margin: 8px 0;">
                                <div style="position: absolute; top: -10px; left: 45%; background: white; padding: 0 8px;">✈️</div>
                            </div>
                            <div style="font-size: 0.8rem; font-weight: 700; color: {'#00A698' if stops==0 else '#D32F2F'};">
                                {'Direct' if stops == 0 else f'{stops} stop'}
                            </div>
                        </div>
                        <div style="text-align: left;">
                            <div style="font-size: 1.6rem; font-weight: 800;">{arr}</div>
                            <div style="color: #68697F; font-size: 1rem; font-weight: 700;">{st.session_state.search_meta['destination']}</div>
                        </div>
                    </div>

                    <div style="flex: 1; text-align: right; border-left: 1px solid #F1F2F8; padding-left: 20px;">
                        {f'<div class="badge badge-cheapest">Cheapest</div>' if price == min_price else ''}
                        <div style="font-size: 0.8rem; color: #68697F;">Total Price</div>
                        <div style="font-size: 2.2rem; font-weight: 800;">{price:.2f} <small style="font-size: 1rem;">{curr}</small></div>
                        <div style="font-size: 0.75rem; color: #00A698; font-weight: 700;">✔ Price Guaranteed</div>
                    </div>
                </div>
                <div class="card-footer">
                    <span>🛡️ Secure Booking &middot; 🌿 -14% CO2</span>
                    <span style="color: #0062E3; font-weight: 700;">Flight Details & Policies &rarr;</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button(f"Select & Shortlist Flight {idx}", key=f"btn_{idx}", use_container_width=True):
            if 'shortlist' not in st.session_state: st.session_state.shortlist = []
            st.session_state.shortlist.append({"airline": airline, "price": price, "curr": curr})
            st.toast(f"Added {airline} to shortlist!")
            st.rerun()
