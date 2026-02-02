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

# --- 2. THE PREMIUM SKYSCANNER THEME ---
st.set_page_config(page_title="AvioX AI", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    
    .stApp { background-color: #F1F2F8; }
    
    /* Premium Flight Card */
    .flight-card {
        background: white;
        border-radius: 12px;
        box-shadow: 0 1px 4px rgba(37,32,31,.1);
        margin-bottom: 16px;
        color: #25201F;
        border: 1px solid #E1E2E9;
        transition: all 0.3s cubic-bezier(.25,.8,.25,1);
    }
    .flight-card:hover {
        box-shadow: 0 8px 24px rgba(37,32,31,.15);
        border-color: #0062E3;
        transform: translateY(-2px);
    }
    
    .card-body { padding: 24px 32px; display: flex; align-items: center; }
    
    .card-footer {
        background: #F9FAFB;
        border-top: 1px solid #E1E2E9;
        padding: 12px 32px;
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        color: #68697F;
        border-radius: 0 0 12px 12px;
    }

    /* Price Badge */
    .badge-cheapest {
        background: #00A698;
        color: white;
        padding: 4px 12px;
        border-radius: 4px;
        font-weight: 700;
        font-size: 0.75rem;
        display: inline-block;
        margin-bottom: 8px;
    }

    /* Timeline Styling */
    .route-visual {
        flex: 3;
        display: flex;
        align-items: center;
        gap: 32px;
        margin: 0 48px;
        padding: 0 24px;
        border-left: 1px solid #E1E2E9;
        border-right: 1px solid #E1E2E9;
    }

    /* Button Overrides */
    .stButton>button {
        background-color: #0062E3 !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        height: 48px !important;
        transition: 0.2s !important;
    }
    .stButton>button:hover { background-color: #004FB8 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. NAVBAR ---
# Improved vertical centering and logo weight
n1, n2, n3 = st.columns([1.8, 5, 1.2])
with n1:
    st.markdown("""
        <div style="padding-top: 10px;">
            <h1 style='color: #0062E3; margin: 0; font-size: 3.2rem; font-weight: 900; letter-spacing: -3px;'>
                Avio<span style='color: #25201F;'>X</span>
            </h1>
        </div>
    """, unsafe_allow_html=True)
with n2:
    st.markdown("<div style='padding-top: 22px;'>", unsafe_allow_html=True)
    user_query = st.text_input("", placeholder="Try 'NYC to London next Friday'", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
with n3:
    st.markdown("<div style='padding-top: 22px;'>", unsafe_allow_html=True)
    search_btn = st.button("Search", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin: 10px 0 30px 0; border: none; height: 1px; background-color: #E1E2E9;'>", unsafe_allow_html=True)

# --- 4. ENGINE LOGIC ---
if user_query:
    if search_btn:
        with st.spinner("✨ Optimizing routes..."):
            try:
                # Robust AI Prompting
                sim_date = datetime.now().strftime("%Y-%m-%d")
                prompt = f"Return ONLY raw JSON. Query: '{user_query}'. Format: {{\"origin\": \"IATA\", \"destination\": \"IATA\", \"date\": \"YYYY-MM-DD\"}}. Ref: Today is {sim_date}."
                
                ai_res = ai_client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0)
                clean_json = ai_res.choices[0].message.content.strip().replace('```json', '').replace('```', '')
                st.session_state.search_meta = json.loads(clean_json)
                
                # API Call
                resp = amadeus.shopping.flight_offers_search.get(
                    originLocationCode=st.session_state.search_meta['origin'].upper(),
                    destinationLocationCode=st.session_state.search_meta['destination'].upper(),
                    departureDate=st.session_state.search_meta['date'],
                    adults=1, max=25
                )
                st.session_state.flights = resp.data
            except Exception as e:
                st.error(f"Engine Log: {e}")

    # --- 5. RESULTS DISPLAY ---
    if 'flights' in st.session_state:
        # Filter Bar
        f1, f2, f3 = st.columns([1, 1, 3])
        with f1: sort_opt = st.selectbox("Sort by", ["Cheapest", "Fastest"])
        with f2: stop_opt = st.selectbox("Stops", ["All", "Direct Only"])
        with f3: st.markdown(f"<p style='text-align:right; padding-top:35px; color:#68697F;'>Found results for <b>{st.session_state.search_meta['origin']} → {st.session_state.search_meta['destination']}</b></p>", unsafe_allow_html=True)

        # Sorting
        df = st.session_state.flights
        if stop_opt == "Direct Only":
            df = [f for f in df if len(f['itineraries'][0]['segments']) == 1]
        
        # Identification of Cheapest
        min_price = min([float(f['price']['total']) for f in df]) if df else 0

        for idx, flight in enumerate(df):
            price = float(flight['price']['total'])
            airline = flight['validatingAirlineCodes'][0]
            it = flight['itineraries'][0]
            stops = len(it['segments']) - 1
            dep = it['segments'][0]['departure']['at'][11:16]
            arr = it['segments'][-1]['arrival']['at'][11:16]
            dur = it['duration'][2:].lower().replace('h', 'h ').replace('m', 'm')
            
            is_cheapest = price == min_price

            st.markdown(f"""
                <div class="flight-card">
                    <div class="card-body">
                        <div style="flex: 1.2;">
                            <img src="https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline.upper()}.svg" width="120" style="margin-bottom:8px;">
                            <div style="font-size: 0.8rem; color: #68697F; font-weight: 600;">Operated by {airline}</div>
                        </div>

                        <div class="route-visual">
                            <div style="text-align: right;">
                                <div style="font-size: 1.7rem; font-weight: 800;">{dep}</div>
                                <div style="color: #68697F; font-size: 0.9rem; font-weight: 600;">{st.session_state.search_meta['origin']}</div>
                            </div>
                            
                            <div style="text-align: center; flex: 1;">
                                <div style="font-size: 0.85rem; color: #68697F; margin-bottom: 4px; font-weight: 600;">{dur}</div>
                                <div style="position: relative; height: 2px; background: #E1E2E9; width: 100%;">
                                    <div style="position: absolute; top: -8px; left: 45%; background: white; padding: 0 8px;">✈️</div>
                                </div>
                                <div style="font-size: 0.85rem; margin-top: 4px; color: {'#00A698' if stops==0 else '#D32F2F'}; font-weight: 700;">
                                    {'Direct' if stops == 0 else f'{stops} stop'}
                                </div>
                            </div>

                            <div style="text-align: left;">
                                <div style="font-size: 1.7rem; font-weight: 800;">{arr}</div>
                                <div style="color: #68697F; font-size: 0.9rem; font-weight: 600;">{st.session_state.search_meta['destination']}</div>
                            </div>
                        </div>

                        <div style="flex: 1; text-align: right;">
                            {f'<div class="badge-cheapest">CHEAPEST</div>' if is_cheapest else ''}
                            <div style="font-size: 0.85rem; color: #68697F; text-transform: uppercase; letter-spacing: 0.5px;">Total Price</div>
                            <div style="font-size: 2.2rem; font-weight: 800; color: #25201F;">{price:.2f} <small style="font-size: 1.1rem; font-weight: 400;">{flight['price']['currency']}</small></div>
                        </div>
                    </div>
                    <div class="card-footer">
                        <span>🛡️ Secure Booking &middot; No hidden fees</span>
                        <span style="color: #0062E3; font-weight: 700; cursor: pointer;">Flight Details & Policies &rarr;</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button(f"Reserve Seat - {airline} {idx}", key=f"f_{idx}", use_container_width=True):
                st.balloons()
                st.success(f"Hold requested for flight {idx} with {airline}!")
