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

amadeus = Client(client_id=AMADEUS_KEY, client_secret=AMADEUS_SECRET)
ai_client = OpenAI(api_key=OPENAI_KEY)

# --- 2. PAGE CONFIG & STYLING ---
st.set_page_config(page_title="AvioX AI", page_icon="✈️", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #020617;
    }
    
    /* Full-width Flight Card */
    .flight-card {
        background: linear-gradient(90deg, #1e293b 0%, #0f172a 100%);
        padding: 25px;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-bottom: 15px;
        color: white;
        width: 100%;
    }
    
    .flight-card:hover {
        border-color: #22d3ee;
        box-shadow: 0 0 20px rgba(34, 211, 238, 0.1);
    }

    .filter-box {
        background-color: #1e293b;
        padding: 10px;
        border-radius: 8px;
        border: 1px solid #334155;
        text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 3. NAVBAR (Logo Left, Search Middle) ---
nav_col1, nav_col2, nav_col3 = st.columns([1, 3, 1])

with nav_col1:
    # Small logo top left
    st.markdown("<h2 style='color: #22d3ee; margin:0;'>AvioX</h2>", unsafe_allow_html=True)

with nav_col2:
    user_query = st.text_input("", placeholder="Where to? (e.g. London to Paris in June)", label_visibility="collapsed")

with nav_col3:
    search_btn = st.button("Search", use_container_width=True)

st.markdown("---")

# --- 4. SEARCH LOGIC ---
if search_btn and user_query:
    with st.spinner("Finding the best routes..."):
        try:
            # AI conversion
            simulated_today = "2026-02-02"
            prompt = f"Convert to JSON: '{user_query}'. Rules: 3-letter IATA, YYYY-MM-DD. Today is {simulated_today}. Return ONLY: {{\"origin\": \"CODE\", \"destination\": \"CODE\", \"date\": \"YYYY-MM-DD\"}}"
            
            ai_res = ai_client.chat.completions.create(model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}], temperature=0)
            data = json.loads(ai_res.choices[0].message.content)

            # --- 5. FILTER BAR (Appears after search) ---
            st.markdown("### Filters & Sorting")
            f_col1, f_col2, f_col3, f_col4 = st.columns(4)
            with f_col1:
                st.selectbox("Stops", ["Non-stop", "1 Stop", "Any"], label_visibility="collapsed")
            with f_col2:
                st.selectbox("Sort By", ["Cheapest", "Fastest", "Early Departure"], label_visibility="collapsed")
            with f_col3:
                st.selectbox("Airline", ["All Airlines", "British Airways", "United", "Lufthansa"], label_visibility="collapsed")
            with f_col4:
                st.write(f"Results for: **{data['origin']} → {data['destination']}**")

            # Amadeus Fetch
            response = amadeus.shopping.flight_offers_search.get(
                originLocationCode=data['origin'], destinationLocationCode=data['destination'],
                departureDate=data['date'], adults=1, max=15
            )

            if response.data:
                st.balloons()
                
                # --- 6. FLIGHT RESULTS (Full Width) ---
                for flight in response.data:
                    price = flight['price']['total']
                    curr = flight['price']['currency']
                    airline = flight['validatingAirlineCodes'][0]
                    itinerary = flight['itineraries'][0]
                    dep = itinerary['segments'][0]['departure']['at'][11:16]
                    arr = itinerary['segments'][-1]['arrival']['at'][11:16]
                    dur = itinerary['duration'][2:].lower().replace('h', 'h ').replace('m', 'm')

                    # Design: Full Width Card
                    st.markdown(f"""
                        <div class="flight-card">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="display: flex; align-items: center; gap: 20px; flex: 1;">
                                    <img src="https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline.upper()}.svg" width="100" style="background:white; padding:5px; border-radius:5px;" onerror="this.src='https://img.icons8.com/clouds/100/airplane-take-off.png'">
                                    <div>
                                        <div style="font-size: 0.8rem; color: #94a3b8;">Airline</div>
                                        <div style="font-weight: bold; color: #22d3ee;">{airline}</div>
                                    </div>
                                </div>
                                <div style="flex: 2; text-align: center;">
                                    <div style="font-size: 2rem; font-weight: 800;">{dep} &rarr; {arr}</div>
                                    <div style="color: #94a3b8;">{dur} | Non-stop</div>
                                </div>
                                <div style="flex: 1; text-align: right;">
                                    <div style="font-size: 2rem; font-weight: 800; color: #22d3ee;">{price} <span style="font-size: 1rem;">{curr}</span></div>
                                    <div style="font-size: 0.7rem; color: #94a3b8;">Incl. taxes & fees</div>
                                </div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Full width button under card
                    if st.button(f"Book {airline} for {price} {curr}", key=f"btn_{flight['id']}", use_container_width=True):
                        st.success("Redirecting to checkout...")
            else:
                st.error("No flights found.")

        except Exception as e:
            st.error(f"Search Error: {e}")
