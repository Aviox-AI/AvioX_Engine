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
    .main { background-color: #020617; }
    .stButton>button { 
        background-color: #22d3ee; 
        color: #020617; 
        font-weight: bold; 
        border-radius: 10px; 
    }
    .flight-card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #334155;
        margin-bottom: 20px;
        color: white;
    }
    .airline-logo {
        border-radius: 8px;
        background: white;
        padding: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("✈️ AvioX Flight Search")
st.write("Talk to your travel agent. Type like a human.")

user_query = st.text_input("Where to?", placeholder="e.g. London to Tokyo next August")

if st.button("Analyze & Search"):
    if not user_query:
        st.warning("Please enter a destination!")
    else:
        with st.spinner("AI is converting your request to flight data..."):
            try:
                # --- 3. THE AI BRAIN ---
                # This gets the actual date from the server clock
                current_date = datetime.now().strftime("%Y-%m-%d") 
                prompt = f"""
                Convert this request to JSON: '{user_query}'
                Rules:
                1. 'origin' and 'destination' must be 3-letter IATA codes.
                2. 'date' must be YYYY-MM-DD. 
                3. Today is {current_date}.
                Return ONLY JSON: {{"origin": "CODE", "destination": "CODE", "date": "YYYY-MM-DD"}}
                """
                
                ai_response = ai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                ai_content = ai_response.choices[0].message.content
                data = json.loads(ai_content)
                st.info(f"Searching: {data['origin']} to {data['destination']} on {data['date']}")

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
                    st.markdown(f"### ✈️ Found {len(response.data)} Flights")
                    
                    # --- 5. SCROLLABLE RESULTS ---
                    with st.container(height=500):
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
                                            <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 0.8rem;">{airline}</p>
                                        </div>
                                        <div style="flex: 2; text-align: center;">
                                            <h2 style="margin: 0; font-size: 1.5rem;">{dep_time} ➔ {arr_time}</h2>
                                            <p style="margin: 0; color: #22d3ee;">{duration} | Non-stop</p>
                                        </div>
                                        <div style="flex: 1; text-align: right;">
                                            <h3 style="margin: 0; color: white;">{price} {currency}</h3>
                                        </div>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button(f"Select {airline} flight", key=f"btn_{flight['id']}"):
                                st.success(f"Selected flight for {price} {currency}!")
                else:
                    st.error("No flights found. Try a different date or city!")

            except Exception as e:
                if hasattr(e, 'response') and e.response:
                    try:
                        error_detail = e.response.result['errors'][0]['detail']
                        st.error(f"Amadeus Error: {error_detail}")
                    except:
                        st.error(f"Engine Error: {e}")
                else:
                    st.error(f"System Error: {e}")

