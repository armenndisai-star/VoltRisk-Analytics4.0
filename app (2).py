import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import io

# 1. PAGE CONFIG & DARK MODE
st.set_page_config(page_title="VoltRisk Analytics", page_icon="⚡", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FFFFFF; }
    section[data-testid="stSidebar"] { background-color: #161B22 !important; border-right: 1px solid #30363D; }
    .signal-box { padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #30363D; margin-bottom: 20px; }
    .beginner-card { background-color: #161B22; padding: 15px; border-radius: 10px; border-left: 5px solid #00FBFF; margin-bottom: 10px; min-height: 120px; }
    
    /* Custom Metric Label Colors */
    .label-cyan { color: #00FBFF; font-weight: bold; margin-bottom: -15px; font-size: 0.9rem; }
    .label-gold { color: #FFD700; font-weight: bold; margin-bottom: -15px; font-size: 0.9rem; }
    .label-red { color: #FF4B4B; font-weight: bold; margin-bottom: -15px; font-size: 0.9rem; }
    .label-green { color: #00FFAA; font-weight: bold; margin-bottom: -15px; font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True)

# 2. SIDEBAR
with st.sidebar:
    st.markdown("<h1 style='text-align: center; color: #00FFAA;'>⚡ VOLTRISK</h1>", unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("Subscription Status")
    license_key = st.text_input("Enter License Key", type="password", help="Project Demo Key: VOLT2026")
    user_status = True if license_key == "VOLT2026" else False
    
    if user_status: st.success("Pro Access Active! ✅")
    else: st.info("Standard Mode (Limited)")

    st.markdown("---")
    ticker = st.text_input("Asset Ticker", value="NVDA").upper()
    investment = st.number_input("Capital Allocation ($)", min_value=10.0, value=1000.0)
    max_sims = 10000 if user_status else 500
    iterations = st.slider("Simulations", 100, max_sims, 500, step=100)
    time_horizon = st.slider("Days to Forecast", 1, 730, 252)
    start_sim = st.button("RUN SIMULATION", use_container_width=True)

# 3. MAIN DASHBOARD
st.title("⚡ :blue[Volt]Risk Analytics")

if start_sim:
    with st.spinner('Calculating...'):
        data = yf.download(ticker, start=(datetime.now() - timedelta(days=1095)), auto_adjust=False)
        spy_data = yf.download("SPY", start=(datetime.now() - timedelta(days=1095)), auto_adjust=False)
        
        if data.empty:
            st.error("Ticker not found.")
        else:
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            if isinstance(spy_data.columns, pd.MultiIndex): spy_data.columns = spy_data.columns.get_level_values(0)

            # Engine
            def run_mc(df, inv, n):
                rets = df['Adj Close'].pct_change().dropna()
                mu, sigma, last = rets.mean(), rets.std(), df['Adj Close'].iloc[-1]
                daily = np.random.normal(mu, sigma, (time_horizon, n))
                paths = np.zeros_like(daily); paths[0] = last * (1 + daily[0])
                for t in range(1, time_horizon): paths[t] = paths[t-1] * (1 + daily[t])
                return (paths / last) * inv

            asset_paths = run_mc(data, investment, iterations)
            final_vals = asset_paths[-1]
            win_prob = (np.sum(final_vals > investment) / iterations) * 100
            tp_95, sl_5, mean_outcome = np.percentile(final_vals, 95), np.percentile(final_vals, 5), np.mean(final_vals)
            avg_max_dd = np.mean(np.min((asset_paths - np.maximum.accumulate(asset_paths, axis=0)) / np.maximum.accumulate(asset_paths, axis=0), axis=0)) * 100

            # 4. GAUGE & SIGNAL
            st.divider()
            c1, c2 = st.columns([1, 1])
            with c1:
                fig_g = go.Figure(go.Indicator(
                    mode="gauge+number", value=win_prob, number={'suffix': "%", 'font': {'color': "#FFFFFF"}},
                    gauge={'axis': {'range': [0, 100]}, 'bar': {'color': "#1b5e20"},
                           'steps': [{'range': [0, 40], 'color': "#FF4B4B"},
                                     {'range': [40, 70], 'color': "#FFD700"},
                                     {'range': [70, 100], 'color': "#00FFAA"}]}))
                fig_g.update_layout(height=280, margin=dict(t=50, b=0), paper_bgcolor='rgba(0,0,0,0)')
                st.plotly_chart(fig_g, use_container_width=True)
            with c2:
                st.markdown("<br><br>", unsafe_allow_html=True)
                if win_prob > 60: st.markdown(f"<div class='signal-box' style='border-color:#00FFAA;'><h2 style='color:#00FFAA;'>BUY SIGNAL</h2><p>Math favors profit.</p></div>", unsafe_allow_html=True)
                else: st.markdown(f"<div class='signal-box'><h2 style='color:#8B949E;'>WAIT</h2><p>Risk is currently too high.</p></div>", unsafe_allow_html=True)

            # 5. MULTI-COLOR METRICS
            st.divider()
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.markdown("<p class='label-cyan'>CURRENT PRICE</p>", unsafe_allow_html=True)
                st.metric("", f"${data['Adj Close'].iloc[-1]:,.2f}")
            with m2:
                st.markdown("<p class='label-gold'>EXPECTED ENDING</p>", unsafe_allow_html=True)
                st.metric("", f"${mean_outcome:,.2f}")
            with m3:
                st.markdown("<p class='label-red'>MAX DANGER (DIP)</p>", unsafe_allow_html=True)
                st.metric("", f"{avg_max_dd:.1f}%")
            with m4:
                st.markdown("<p class='label-green'>SAFETY FLOOR</p>", unsafe_allow_html=True)
                st.metric("", f"${sl_5:,.2f}")

            # 6. CHART WITH MATCHING COLORS
            st.subheader("🔍 Market Benchmark & Volatility Bands")
            fig = go.Figure()
            days = list(range(time_horizon))
            
            # Shaded Background Paths (Cyan)
            for i in range(min(50, iterations)):
                fig.add_trace(go.Scatter(x=days, y=asset_paths[:, i], line=dict(color='rgba(0, 251, 255, 0.05)', width=1), hoverinfo='none', showlegend=False))
            
            # Gold Line (Expected Ending)
            fig.add_trace(go.Scatter(x=days, y=np.mean(asset_paths, axis=1), name="Expected Outcome", line=dict(color='#FFD700', width=4)))
            
            # Green Line (Safety Floor / 5th Percentile)
            low_path = np.percentile(asset_paths, 5, axis=1)
            fig.add_trace(go.Scatter(x=days, y=low_path, name="Safety Floor (5%)", line=dict(color='#00FFAA', width=2, dash='dash')))
            
            # Red H-Line (Max Danger / Dip visualization)
            if user_status:
                spy_paths = run_mc(spy_data, investment, 1000)
                fig.add_trace(go.Scatter(x=days, y=np.mean(spy_paths, axis=1), name="S&P 500", line=dict(color='white', dash='dot')))

            fig.update_layout(template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', height=500)
            st.plotly_chart(fig, use_container_width=True)

            # 7. ANALYSIS
            st.divider()
            st.subheader("📊 Strategic Analysis")
            b1, b2, b3 = st.columns(3)
            with b1: st.markdown("<div class='beginner-card'><b style='color:#00FFAA;'>1. Win Probability</b><br>The chance of your investment growing. Experts look for 60%+.</div>", unsafe_allow_html=True)
            with b2: st.markdown("<div class='beginner-card'><b style='color:#FF4B4B;'>2. The Stomach Test</b><br>Max Danger shows the biggest expected dip. If this number is too high, lower your investment.</div>", unsafe_allow_html=True)
            with b3: st.markdown("<div class='beginner-card'><b style='color:#FFD700;'>3. Target Outcome</b><br>The Gold line shows where the stock is likely to land. Compare this to the White market line.</div>", unsafe_allow_html=True)
else:
    st.info("👋 **Welcome to VoltRisk.** Use 'VOLT2026' for Pro Access.")