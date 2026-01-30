import streamlit as st
from amadeus import Client
from openai import OpenAI
import json
from datetime import datetime

# --- 1. THE SAFETY SWITCH ---
# This looks for keys in the "Vault" first. If not found, it uses your local testing keys.
try:
    AMADEUS_KEY = st.secrets["AMADEUS_KEY"]
    AMADEUS_SECRET = st.secrets["AMADEUS_SECRET"]
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except:
    # PASTE YOUR REAL KEYS HERE FOR LOCAL TESTING
    AMADEUS_KEY = ""
    AMADEUS_SECRET = ""
    OPENAI_KEY = ""

# Initialize Clients
amadeus = Client(client_id=AMADEUS_KEY, client_secret=AMADEUS_SECRET)
ai_client = OpenAI(api_key=OPENAI_KEY)

# --- 2. APP INTERFACE ---
st.set_page_config(page_title="AvioX AI", page_icon="✈️", layout="centered")

st.markdown("""
    <style>
    .main { background-color: #020617; }
    .stButton>button { background-color: #22d3ee; color: #020617; font-weight: bold; border-radius: 10px; }
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
                # --- 3. THE AI BRAIN (FORCING CORRECT FORMATS) ---
                current_date = "2026-01-30" # Today's date for AI context
                prompt = f"""
                Convert this request to JSON: '{user_query}'
                Rules:
                1. 'origin' and 'destination' must be 3-letter IATA codes (e.g. NYC, LON).
                2. 'date' must be YYYY-MM-DD. 
                3. If no year is mentioned, use 2026.
                4. Today is {current_date}.
                Return ONLY JSON: {{"origin": "CODE", "destination": "CODE", "date": "YYYY-MM-DD"}}
                """
                
                ai_response = ai_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0
                )
                
                data = json.loads(ai_response.choices[0].message.content)
                
                # Show the user what the AI understood
                st.info(f"Searching: {data['origin']} to {data['destination']} on {data['date']}")

                # --- 4. THE FLIGHT ENGINE (AMADEUS) ---
                response = amadeus.shopping.flight_offers_search.get(
                    originLocationCode=data['origin'],
                    destinationLocationCode=data['destination'],
                    departureDate=data['date'],
                    adults=1
                )

                if response.data:
                    st.balloons()
                    cheapest = response.data[0]
                    price = cheapest['price']['total']
                    currency = cheapest['price']['currency']
                    
                    st.success(f"✅ Found it! Best total price:")
                    st.metric(label="Flight Price", value=f"{price} {currency}")
                    st.caption(f"Validating Airline: {cheapest['validatingAirlineCodes'][0]}")
                else:
                    st.error("No flights found for those specific cities or dates.")

            except Exception as e:
                # This helps us see if the error is from AI or Amadeus
                st.error(f"Engine Error: {e}")