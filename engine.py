from datetime import datetime
import streamlit as st
from amadeus import Client
from openai import OpenAI
import json

# --- 1. THE SAFETY SWITCH ---
try:
    AMADEUS_KEY = st.secrets["AMADEUS_KEY"]
    AMADEUS_SECRET = st.secrets["AMADEUS_SECRET"]
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except Exception as e:
    st.error(f"❌ Setup Error: Missing keys in Streamlit Secrets. ({e})")
    st.stop()

# Initialize Clients
amadeus = Client(client_id=AMADEUS_KEY, client_secret=AMADEUS_SECRET)
ai_client = OpenAI(api_key=OPENAI_KEY)

# --- 2. APP INTERFACE ---
st.set_page_config(page_title="AvioX AI", page_icon="✈️", layout="centered")

# Custom Styling
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        background-color: #020617;
    }
    .main { background-color: #020617; }
    .stButton>button { 
        background-color: #22d3ee; 
        color: #020617; 
        font-weight: bold; 
        border-radius: 10px;
        border: none;
        height: 3rem;
    }
    .flight-card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #334155;
        margin-bottom: 20px;
        color: white;
        transition: transform 0.2s;
    }
    .flight-card:hover {
        transform: translateY(-5px);
        border-color: #22d3ee;
    }
    .airline-logo {
        border-radius: 8px;
        background: white;
        padding: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

# Header Section
st.markdown("""
    <div style="text-align: center; padding: 20px 0px;">
        <h1 style="color: #22d3ee; font-size: 3rem; margin-bottom: 0;">AvioX AI</h1>
        <p style="color: #94a3b8; font-size: 1.2rem;">Next-Gen Flight Intelligence</p>
    </div>
""", unsafe_allow_html=True)

# Input Section
user_query = st.text_input("", placeholder="Where would you like to fly? (e.g. London to JFK in March)", label_visibility="collapsed")

if st.button("Search Flights", use_container_width=True):
    if not user_query:
        st.warning("Please enter a destination!")
    else:
        with st.spinner("Analyzing route and fetching prices..."):
            try:
                # --- 3. THE AI BRAIN ---
                # We use 2026 to stay within Amadeus Test Tier's valid range
                simulated_today = "2026-02-02" 
                prompt = f"""
                Convert this request to JSON: '{user_query}'
                Rules:
                1. 'origin' and 'destination' must be 3-letter IATA codes.
                2. 'date' must be YYYY-MM-DD. 
                3. Today is {simulated_today}.
                Return ONLY JSON: {{"origin": "CODE", "destination": "CODE", "date": "YYYY-MM-DD"}}
                """
                
                ai_response = ai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                data = json.loads(ai_response.choices[0].message.content)
                st.info(f"📍 {data['origin']} to {data['destination']} | 📅 {data['date']}")

                # --- 4. THE FLIGHT ENGINE (AMADEUS) ---
                response = amadeus.shopping.flight_offers_search.get(
                    originLocationCode=data['origin'],
                    destinationLocationCode=data['destination'],
                    departureDate=data['date'],
                    adults=1,
                    max=20
                )

                if response.data:
                    st.balloons()
                    
                    # --- 5. SCROLLABLE RESULTS ---
                    with st.container(height=600):
                        for flight in response.data:
                            price = flight['price']['total']
                            currency = flight['price']['currency']
                            airline = flight['validatingAirlineCodes'][0]
                            itinerary = flight['itineraries'][0]
                            
                            dep_time = itinerary['segments'][0]['departure']['at'][11:16]
                            arr_time = itinerary['segments'][-1]['arrival']['at'][11:16]
                            duration = itinerary['duration'][2:].lower().replace('h', 'h ').replace('m', 'm')

                            st.markdown(f"""
                                <div class="flight-card">
                                    <div style="display: flex; justify-content: space-between; align-items: center;">
                                        <div style="flex: 1;">
                                            <img class="airline-logo" src="https://assets.duffel.com/img/airlines/for-light-background/full-color-lockup/{airline.upper()}.svg" width="80" onerror="this.src='https://img.icons8.com/clouds/100/airplane-take-off.png'">
                                            <p style="margin: 5px 0 0 0; color: #94a3b8; font-weight: bold;">{airline}</p>
                                        </div>
                                        <div style="flex: 2; text-align: center;">
                                            <h2 style="margin: 0; font-size: 1.8rem; color: #f8fafc;">{dep_time} &rarr; {arr_time}</h2>
                                            <p style="margin: 0; color: #22d3ee; font-size: 0.9rem;">{duration} | Direct</p>
                                        </div>
                                        <div style="flex: 1; text-align: right;">
                                            <p style="margin: 0; color: #94a3b8; font-size: 0.7rem; text-transform: uppercase;">Best Price</p>
                                            <h2 style="margin: 0; color: #22d3ee;">{price} <span style="font-size: 1rem;">{currency}</span></h2>
                                        </div>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button(f"Select {airline} Flight", key=f"btn_{flight['id']}", use_container_width=True):
                                st.success(f"Selected! Price: {price} {currency}")
                else:
                    st.error("No flights found for this route on this date.")

            except Exception as e:
                if hasattr(e, 'response') and e.response:
                    try:
                        error_detail = e.response.result['errors'][0]['detail']
                        st.error(f"Amadeus Error: {error_detail}")
                    except:
                        st.error(f"Engine Error: {e}")
                else:
                    st.error(f"System Error: {e}")
