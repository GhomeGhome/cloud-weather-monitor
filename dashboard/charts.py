from datetime import timezone, timedelta

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

_DISPLAY_TZ = timezone(timedelta(hours=2))

# Colour per metric
_COLOURS = {
    "temperature_c": "#F97316",   # orange
    "humidity_pct":  "#38BDF8",   # sky blue
    "eco2_ppm":      "#A78BFA",   # violet
    "tvoc_ppb":      "#4ADE80",   # green
}
_DEFAULT_COLOUR = "#94A3B8"


def line_chart(df: pd.DataFrame, x_col: str, y_col: str, title: str, y_label: str) -> None:
    if df.empty or y_col not in df.columns:
        st.info(f"No data for {title}.")
        return

    plot_df = df[[x_col, y_col]].dropna(subset=[y_col]).copy()
    if plot_df.empty:
        st.info(f"No data for {title}.")
        return

    try:
        plot_df[x_col] = plot_df[x_col].dt.tz_convert(_DISPLAY_TZ)
    except Exception:
        pass

    colour = _COLOURS.get(y_col, _DEFAULT_COLOUR)

    fig, ax = plt.subplots(figsize=(11, 2.8))
    fig.patch.set_facecolor("#0F172A")
    ax.set_facecolor("#111827")

    x = plot_df[x_col]
    y = plot_df[y_col].astype(float)

    ax.fill_between(x, y, alpha=0.18, color=colour)
    ax.plot(x, y, linewidth=2, color=colour, solid_capstyle="round")

    # Subtle min/max markers
    if len(y) > 2:
        ax.scatter([x.iloc[y.argmin()]], [y.min()], color=colour, s=30, zorder=5, alpha=0.8)
        ax.scatter([x.iloc[y.argmax()]], [y.max()], color=colour, s=30, zorder=5, alpha=0.8)

    ax.set_title(title, color="#94A3B8", fontsize=10.5, pad=10, loc="left", fontweight="600")
    ax.set_ylabel(y_label, color="#475569", fontsize=8.5)
    ax.tick_params(colors="#475569", labelsize=8)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %Hh"))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
    fig.autofmt_xdate(rotation=30, ha="right")

    for spine in ax.spines.values():
        spine.set_edgecolor("#1E3A5F")

    ax.grid(True, color="#1E293B", alpha=0.8, linestyle="--", linewidth=0.6)
    ax.set_xlim(x.min(), x.max())

    fig.tight_layout(pad=0.6)
    st.pyplot(fig)
    plt.close(fig)
