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

# --- 2. PAGE CONFIG & PREMIUM THEME ---
st.set_page_config(page_title="AvioX | Elite Travel", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* Global Reset */
    .stApp { background-color: #F8F9FC; }
    h1, h2, h3, p, div { font-family: 'Inter', sans-serif; }
    
    /* Integrated Flight Card */
    .flight-card {
        background: white;
        border-radius: 16px 16px 0 0;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        border: 1px solid #EEF0F6;
        margin-bottom: 0;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .flight-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0,98,227,0.12);
        border-color: #0062E3;
    }
    
    .card-body { padding: 28px 40px; display: flex; align-items: center; }
    
    .card-footer {
        background: #F8FAFC;
        border-top: 1px solid #EEF0F6;
        padding: 12px 40px;
        display: flex;
        justify-content: space-between;
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 500;
    }

    /* Route Visualizer */
    .route-visual {
        flex: 3;
        display: flex;
        align-items: center;
        gap: 40px;
        margin: 0 50px;
        padding: 0 30px;
        border-left: 2px solid #F1F5F9;
        border-right: 2px solid #F1F5F9;
    }

    /* Price Insight Badges */
    .badge {
        padding: 6px 12px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 8px;
        display: inline-block;
    }
    .badge-cheapest { background: #ECFDF5; color: #059669; border: 1px solid #A7F3D0; }
    
    /* "Select" Button Integration */
    .stButton>button {
        background-color: #0062E3 !important;
        color: white !important;
        border-radius: 0 0 16px 16px !important;
        height: 55px !important;
        border: none !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        margin-top: -1px !important;
        width: 100%;
        transition: all 0.2s;
    }
    .stButton>button:hover { 
        background-color: #0051C0 !important; 
        letter-spacing: 1px;
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: white;
        border-right: 1px solid #EEF0F6;
    }
    
    /* Input Field Polish */
    .stTextInput>div>div>input {
        height: 55px;
        font-size: 1.1rem;
        border-radius: 12px;
        border: 2px solid #E2E8F0;
        padding-left: 20px;
    }
    .stTextInput>div>div>input:focus {
        border-color: #0062E3;
        box-shadow: 0 0 0 4px rgba(0,98,227,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. SMART SIDEBAR (Shortlist) ---
with st.sidebar:
    st.markdown("### 🔖 Shortlist")
    st.markdown("Save flights here to compare.")
    
    if 'shortlist' not in st.session_state:
        st.session_state.shortlist = []

    if not st.session_state.shortlist:
        st.info("Your shortlist is empty.")
    else:
        for i, item in enumerate(st.session_state.shortlist):
            st.markdown(f"""
                <div style="background: #F8FAFC; padding: 15px; border-radius: 10px; border: 1px solid #EEF0F6; margin-bottom: 10px;">
                    <div style="font-weight: 700; color: #1E293B;">{item['airline']}</div>
                    <div style="font-size: 0.9rem; color: #64748B;">{item['route']}</div>
                    <div style="font-size: 1.2rem; font-weight: 800; color: #0062E3; margin-top: 5px;">{item['price']} {item['curr']}</div>
                </div>
            """, unsafe_allow_html=True)
        
        if st.button("Clear All", key="clear_list"):
            st.session_state.shortlist = []
            st.rerun()

# --- 4. NAVIGATION HEADER ---
n1, n2, n3 = st.columns([1.5, 4, 1.2])
with n1:
    st.markdown("""
        <div style="display: flex; align-items: center; height: 75px;">
            <h1 style='color: #0062E3; margin: 0; font-size: 3rem; font-weight: 900; letter-spacing: -2px;'>
                Avio<span style='color: #1E293B;'>X</span>
            </h1>
        </div>
    """, unsafe_allow_html=True)

with n2:
    st.markdown("<div style='padding-top: 10px;'>", unsafe_allow_html=True)
    user_query = st.text_input("", placeholder="Try 'New York to London first week of October'", label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)

with n3:
    st.markdown("<div style='padding-top: 10px;'>", unsafe_allow_html=True)
    search_btn = st.button("Search Flights", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# --- 5. SEARCH ENGINE LOGIC ---
if user_query and search_btn:
    with st.spinner("Scanning global routes..."):
        try:
            # 1. AI Parsing
            sim_date = datetime.now().strftime("%Y-%m-%d")
            prompt = f"""
            Extract entities from: '{user_query}'.
            Return JSON: {{"origin": "IATA_CODE", "destination": "IATA_CODE", "date": "YYYY-MM-DD"}}
            Rules: Today is {sim_date}. If date is vague (e.g. 'next week'), calculate it.
            """
            
            ai_res = ai_client.chat.completions.create(
                model="gpt-3.5-turbo", 
                messages=[{"role": "user", "content": prompt}], 
                temperature=0
            )
            
            # Robust JSON Cleaning
            raw_content = ai_res.choices[0].message.content
            clean_json = raw_content.replace('```json', '').replace('```', '').strip()
            st.session_state.search_meta = json.loads(clean_json)
            
            # 2. Amadeus API Call
            resp = amadeus.shopping.flight_offers_search.get(
                originLocationCode=st.session_state.search_meta['origin'].upper(),
                destinationLocationCode=st.session_state.search_meta['destination'].upper(),
                departureDate=st.session_state.search_meta['date'],
                adults=1, 
                max=15
            )
            st.session_state.flights = resp.data
            
        except Exception as e:
            st.error(f"Search Error: {e}")

# --- 6. RESULTS DISPLAY ---
if 'flights' in st.session_state and st.session_state.flights:
    # Filter Bar
    f1, f2, f3 = st.columns([1, 1, 3])
    with f1: sort_opt = st.selectbox("Sort By", ["Cheapest First", "Fastest First"])
    with f2: stop_opt = st.selectbox("Stops", ["Any", "Direct Only"])
    with f3: 
        meta = st.session_state.search_meta
        st.markdown(f"<div style='text-align: right; padding-top: 35px; color: #64748B; font-weight: 500;'>Found {len(st.session_state.flights)} results for <b>{meta['origin']} → {meta['destination']}</b></div>", unsafe_allow_html=True)

    # Data Processing
    df = st.session_state.flights
    if stop_opt == "Direct Only":
        df = [f for f in df if len(f['itineraries'][0]['segments']) == 1]
    
    # Sorting
    if sort_opt == "Cheapest First":
        df = sorted(df, key=lambda x: float(x['price']['total']))
    else:
        # Simple duration sort (approximate by string length for demo speed)
        df = sorted(df, key=lambda x: x['itineraries'][0]['duration'])

    # Find Cheapest Price for Badge
    min_price = min([float(f['price']['total']) for f in df]) if df else 0

    # Render Cards
    for idx, flight in enumerate(df):
        price = float(flight['price']['total'])
        curr = flight['price']['currency']
        airline = flight['validatingAirlineCodes'][0]
        it = flight['itineraries'][0]
        
        # Time Formatting
        dep_raw = it['segments'][0]['departure']['at']
        arr_raw = it['segments'][-1]['arrival']['at']
        dep_time = dep_raw[11:16]
        arr_time = arr_raw[11:16]
        
        # Duration Cleaning
        dur = it['duration'][2:].lower().replace('h', 'h ').replace('m', 'm')
        stops = len(it['segments']) - 1
        
        is_cheapest = (price == min_price)

        st.markdown(f"""
            <div class="flight-card">
                <div class="card-body">
                    <div style="flex: 1;">
                        <img src="https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline.upper()}.svg" width="100" style="margin-bottom: 8px;">
                        <div style="font-size: 0.8rem; color: #64748B; font-weight: 600;">Operated by {airline}</div>
                    </div>

                    <div class="route-visual">
                        <div style="text-align: right;">
                            <div style="font-size: 1.8rem; font-weight: 800; color: #1E293B; line-height: 1;">{dep_time}</div>
                            <div style="color: #64748B; font-size: 1rem; font-weight: 600; margin-top: 4px;">{st.session_state.search_meta['origin']}</div>
                        </div>
                        
                        <div style="text-align: center; flex: 1;">
                            <div style="font-size: 0.85rem; color: #64748B; font-weight: 600; margin-bottom: 6px;">{dur}</div>
                            <div style="position: relative; height: 2px; background: #E2E8F0; width: 100%;">
                                <div style="position: absolute; top: -11px; left: 50%; transform: translateX(-50%); background: white; padding: 0 8px;">
                                    <span style="font-size: 1.2rem;">✈️</span>
                                </div>
                            </div>
                            <div style="font-size: 0.85rem; margin-top: 8px; font-weight: 700; color: {'#059669' if stops==0 else '#EF4444'};">
                                {'Direct Flight' if stops == 0 else f'{stops} Stop(s)'}
                            </div>
                        </div>

                        <div style="text-align: left;">
                            <div style="font-size: 1.8rem; font-weight: 800; color: #1E293B; line-height: 1;">{arr_time}</div>
                            <div style="color: #64748B; font-size: 1rem; font-weight: 600; margin-top: 4px;">{st.session_state.search_meta['destination']}</div>
                        </div>
                    </div>

                    <div style="flex: 1; text-align: right; border-left: 1px solid #F1F5F9; padding-left: 30px;">
                        {f'<div class="badge badge-cheapest">BEST PRICE</div>' if is_cheapest else ''}
                        <div style="font-size: 0.85rem; color: #64748B; font-weight: 500; margin-bottom: 2px;">Per adult</div>
                        <div style="font-size: 2.2rem; font-weight: 800; color: #0F172A; letter-spacing: -1px;">{price:.0f} <small style="font-size: 1.1rem; color: #64748B; font-weight: 600;">{curr}</small></div>
                    </div>
                </div>
                
                <div class="card-footer">
                    <div style="display: flex; gap: 20px;">
                        <span>🛍️ <b>Personal Item</b> included</span>
                        <span>🔄 <b>Flexible</b> rebooking</span>
                    </div>
                    <div style="color: #0062E3; font-weight: 700; cursor: pointer;">Flight Details &rarr;</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # The Action Button
        btn_col1, btn_col2 = st.columns([1, 11]) # Hack to hide the button key if needed
        if st.button(f"Select Flight & Add to Shortlist", key=f"btn_{idx}", use_container_width=True):
            st.session_state.shortlist.append({
                "airline": airline,
                "price": price,
                "curr": curr,
                "route": f"{st.session_state.search_meta['origin']} -> {st.session_state.search_meta['destination']}"
            })
            st.toast(f"✅ Added {airline} flight to your shortlist!", icon="✈️")
            st.rerun()

elif 'flights' in st.session_state and not st.session_state.flights:
    st.warning("No flights found. Try a different date or route (e.g. London to JFK in October).")
