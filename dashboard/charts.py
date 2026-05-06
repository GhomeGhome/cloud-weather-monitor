import matplotlib.pyplot as plt
import streamlit as st


def line_chart(df, x_col: str, y_col: str, title: str, y_label: str) -> None:
    if df.empty:
        st.info(f"No data for {title}.")
        return
    fig, ax = plt.subplots(figsize=(9, 3))
    ax.plot(df[x_col], df[y_col])
    ax.set_title(title)
    ax.set_xlabel("Time")
    ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)
