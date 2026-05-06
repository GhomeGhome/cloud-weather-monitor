import streamlit as st

from charts import line_chart
from data import indoor_history, latest_indoor, latest_outdoor, recent_events


st.set_page_config(page_title="Cloud Weather Monitor", layout="wide")
st.title("Cloud Analytics Weather Monitor")

device_id = st.sidebar.text_input("Device ID", value="core2-main")
history_days = st.sidebar.slider("History days", min_value=1, max_value=30, value=7)
page = st.sidebar.radio("Navigation", ["Realtime", "History", "Events"])

if page == "Realtime":
    st.subheader("Latest Conditions")
    indoor = latest_indoor(device_id)
    outdoor = latest_outdoor()
    col1, col2 = st.columns(2)

    with col1:
        st.write("Indoor")
        if indoor.empty:
            st.warning("No indoor data.")
        else:
            row = indoor.iloc[0]
            st.metric("Temperature (C)", f"{row['temperature_c']:.1f}")
            st.metric("Humidity (%)", f"{row['humidity_pct']:.1f}")
            st.metric("TVOC (ppb)", int(row["tvoc_ppb"]) if row["tvoc_ppb"] is not None else "n/a")
            st.metric("eCO2 (ppm)", int(row["eco2_ppm"]) if row["eco2_ppm"] is not None else "n/a")

    with col2:
        st.write("Outdoor")
        if outdoor.empty:
            st.warning("No outdoor data.")
        else:
            row = outdoor.iloc[0]
            st.metric("Temperature (C)", f"{row['temperature_c']:.1f}")
            st.metric("Humidity (%)", f"{row['humidity_pct']:.1f}")
            st.write(f"Condition: {row['weather_main']} - {row['weather_description']}")
            st.write(f"Weather icon code: {row['weather_icon']}")

if page == "History":
    st.subheader("Historical Trends")
    history = indoor_history(device_id=device_id, days=history_days)
    line_chart(history, "event_ts", "temperature_c", "Indoor Temperature", "C")
    line_chart(history, "event_ts", "humidity_pct", "Indoor Humidity", "%")
    line_chart(history, "event_ts", "eco2_ppm", "Indoor eCO2", "ppm")
    line_chart(history, "event_ts", "tvoc_ppb", "Indoor TVOC", "ppb")

if page == "Events":
    st.subheader("Recent Events and Alerts")
    events = recent_events(device_id=device_id, limit=100)
    if events.empty:
        st.info("No events yet.")
    else:
        st.dataframe(events, use_container_width=True)
