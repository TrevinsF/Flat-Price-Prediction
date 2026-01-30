import streamlit as st
import pandas as pd
import pickle
import altair as alt
import numpy as np
import requests

# Currency Fetching
@st.cache_data(ttl=86400)  # Cache for 24 hours (86400 seconds)
def get_conversion_rates():
    try:
        url = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/rub.json"
        response = requests.get(url, timeout=10)
        data = response.json()
        return {
            "gbp": data['rub']['gbp'],
            "lkr": data['rub']['lkr']
        }
    except Exception as e:
        # Fallback to hardcoded rates if API is down
        return {"gbp": 0.0098, "lkr": 4.11}

rates = get_conversion_rates()

# Page config
st.set_page_config(
    page_title="Flat Price Predictor",
    layout="wide"
)

# Load styles
def local_css(styles):
    with open(styles) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

local_css("styles.css")

# Load model
@st.cache_resource
def load_model():
    with open('flat_price_model.pkl', 'rb') as f:
        return pickle.load(f)

model = load_model()

# Title
st.markdown('<div class="main-title">Flat Price Predictor</div>', unsafe_allow_html=True)

# Form
with st.container(border=True):
    # Apartment Dimensions
    st.subheader("Apartment Dimensions (m²)")
    cols = st.columns(3)

    with cols[0]:
        kitchen_area = st.number_input(
            "Kitchen Area", min_value=7, max_value=26, value=15, step=1
        )
    with cols[1]:
        bath_area = st.number_input(
            "Bathroom Area", min_value=7, max_value=36, value=20, step=1,
            help = "Areas 16m² and above are classified as 2 bathroom layouts in the model."
        )
    with cols[2]:
        other_area = st.number_input(
            "Other Area", min_value=12.0, max_value=91.0, value=30.0, step=0.5
        )

    # Extras
    st.subheader("Extras and Other Rooms")
    cols = st.columns([1,1,1,1.5])

    with cols[0]:
        display_count = st.slider(
            "Number of Extras", min_value=1, max_value=3, value=1,
            help="All have at least one Balcony/Loggia."
        )
        extra_area_count = display_count - 1 # Map back to 0, 1, 2 for the model

    with cols[1]:
        extra_area = st.number_input(
            "Total Extra Area (m²)", min_value=0, max_value=20, value=5, step=1
        )

    with cols[2]:
        extra_area_type = st.radio(
            "Extra Type", ["Balcony", "Loggia"], horizontal=True,
        )

    max_rooms_allowed = max(1, int(other_area // 10))
    with cols[3]:
        rooms_count = st.slider(
            "Number of Other Rooms",
            min_value=0, max_value=max_rooms_allowed, value=min(1, max_rooms_allowed), step=1,
            help=f"The max updates dynamically when the Other Area value changes."
        )

    st.divider()

    # Calculations
    total_area_val = kitchen_area + bath_area + other_area + (extra_area / 3.0)
    bath_count_val = 2 if bath_area >= 16 else 1
    with st.container(border=True):
        cols = st.columns([1, 2])
        cols[0].metric("Total Area", f"{total_area_val:.2f} m²")
        cols[1].metric("Number of Bathrooms", f"{bath_count_val}")

    # Chart
    with st.container(border=True):
        room_order = ['Kitchen', 'Bathroom', 'Other', 'Extra']
        room_sizes = [kitchen_area, bath_area, other_area, extra_area]

        layout_data = pd.DataFrame({'Room': room_order, 'Size': room_sizes})
        layout_data = layout_data[layout_data['Size'] > 0]

        area_chart = alt.Chart(layout_data).mark_bar(cornerRadius=5).encode(
            x=alt.X('sum(Size):Q', stack='normalize', axis=None),
            color=alt.Color('Room:N', scale=alt.Scale(scheme='set2'), sort=room_order,
            legend=alt.Legend(orient='bottom', direction='horizontal', title=None, offset=-10)),
            tooltip=['Room', 'Size'],
            order=alt.Order('Room_Sort_Index:Q')
        ).transform_calculate(
            Room_Sort_Index=f"indexof({room_order}, datum.Room)"
        ).properties(
            height=80,
            background='transparent'
        ).configure_legend(
            padding=0,
            symbolSize=50,
        )

        st.caption("Area Composition")
        st.altair_chart(area_chart, width="stretch")

    st.divider()

    # Building and Floor Information
    st.subheader("Building and Floor Information")
    cols = st.columns(2)

    with cols[0]:
        year = st.slider(
            "Year Built", min_value=1900, max_value=2020, value=1980, step=1
        )
        ceil_height = st.number_input(
            "Ceiling Height (m)", min_value=2.5, max_value=5.0, value=2.70, step=0.05,
        )

    with cols[1]:
        floor_max = st.slider(
            "Total Floors", min_value=1, max_value=23, value=14, step=1
        )
        floor = st.slider(
            "Apartment Floor",
            min_value=1, max_value=floor_max, value=min(6, floor_max), step=1,
            help = "The maximum floors are limited based on the current number of Total Floors."
        )

    st.divider()

    # Utilities
    st.subheader("Utilities")
    cols = st.columns(3)

    with cols[0]:
        gas = st.toggle("Gas Supply", value=True)
    with cols[1]:
        hot_water = st.toggle("Hot Water", value=True)
    with cols[2]:
        central_heating = st.toggle("Central Heating", value=True)

    st.divider()

    # Location
    st.subheader("Location")
    district = st.selectbox(
        "District",
        [
            "Centralnyj", "Petrogradskij", "Moskovskij", "Nevskij",
            "Kirovskij", "Krasnoselskij", "Vyborgskij"
        ], index=2
    )

    st.divider()
    st.write("")
    st.write("")

    submitted = st.button(
        "Calculate Estimated Price", type="primary", width="stretch"
    )

if submitted:
    input_data = {
        'kitchen_area': kitchen_area,
        'bath_area': bath_area,
        'other_area': other_area,
        'gas': 'Yes' if gas else 'No',
        'hot_water': 'Yes' if hot_water else 'No',
        'central_heating': 'Yes' if central_heating else 'No',
        'extra_area': extra_area,
        'extra_area_count': extra_area_count,
        'year': year,
        'ceil_height': ceil_height,
        'floor_max': floor_max,
        'floor': floor,
        'total_area': total_area_val,
        'bath_count': bath_count_val,
        'extra_area_type_name': extra_area_type.lower(),
        'district_name': district,
        'rooms_count': rooms_count,
    }

    df_input = pd.DataFrame([input_data])
    log_price = model.predict(df_input)[0]
    price = np.expm1(log_price)

    # Price display
    @st.dialog(" ", width="medium")
    def show_price(price, total_area_val):
        price_per_m2 = price / total_area_val
        price_gbp = price * rates['gbp']
        price_lkr = price * rates['lkr']
        st.markdown(f"""
            <div class="price-box">
                <div class="price-title">Estimated Market Value</div>
                <div class="price-amount">{price:,.0f} ₽</div>
                <div class="price-per-m2">{price_per_m2:,.0f} ₽ / m²</div>
                <div class="horizontal-line">
                    <div class="currency-box">
                        <div class="currency-label">British Pound</div>
                        <div class="currency-value">£{price_gbp:,.0f}</div>
                    </div>
                    <div class="vertical-line"></div>        
                    <div class="currency-box">
                        <div class="currency-label">Sri Lankan Rupee</div>
                        <div class="currency-value">Rs. {price_lkr:,.0f}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    show_price(price, total_area_val)
