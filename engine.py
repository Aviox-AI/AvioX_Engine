import streamlit as st
from amadeus import Client
from openai import OpenAI
import json

# --- 1. THE SAFETY SWITCH ---
# We use a more precise way to load secrets to prevent the "Empty Key" error.
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
        width: 100%;
    }
    .flight-card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #334155;
        margin-bottom: 10px;
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
                current_date = "2026-01-30" 
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
                
                data = json.loads(ai_response.choices[0].message.content)
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
                    st.markdown("### ✈️ Top Flight Results")
                    
                    for flight in response.data[:5]:
                        price = flight['price']['total']
                        currency = flight['price']['currency']
                        airline = flight['validatingAirlineCodes'][0]
                        
                        # --- 5. THE PRO FLIGHT CARDS ---
                        with st.container():
                            col1, col2, col3 = st.columns([1, 2, 1])
                            
                            with col1:
                                st.write(f"**{airline}**")
                                st.caption("Airline")
                                
                            with col2:
                                st.write("Standard Economy")
                                st.caption("Best Available Fare")
                                
                            with col3:
                                st.metric(label="Total", value=f"{price} {currency}")
                                # Key uses flight ID to stay unique
                                if st.button(f"Select", key=flight['id']):
                                    st.success(f"Selected {airline}!")

                            st.divider() 
                else:
                    st.error("No flights found. Try a different date or city!")

            except Exception as e:
                st.error(f"Engine Error: {e}")
