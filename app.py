
# app.py
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yfinance as yf
from streamlit_autorefresh import st_autorefresh

from stock_data import (
    nifty_50_dict,
    fetch_stock_data,
    process_data,
    calculate_metrics,
    add_technical_indicators
)
from forecasting import forecast_pct_change 
from forecasting import get_suggestions

# Set page configuration
st.set_page_config(layout="wide", page_title="Real Time Stock & Stock Forecast Dashboard")

# App Mode Selection
app_mode = st.sidebar.radio("Choose App Mode", ["Real Time Stock Dashboard", "Stock Forecast"])

if app_mode == "Real Time Stock Dashboard":
    st.title("Real Time Stock Dashboard")
    
    # Sidebar inputs for chart parameters
    st.sidebar.header("Chart Parameters")
    company_name = st.sidebar.selectbox("Select Company", list(nifty_50_dict.keys()))
    ticker = nifty_50_dict[company_name]
    time_period = st.sidebar.selectbox("Time Period", ["1d", "1wk", "1mo", "1y", "max"])
    chart_type = st.sidebar.selectbox("Chart Type", ["Candlestick", "Line"])
    indicators = st.sidebar.multiselect("Technical Indicators", ["SMA 20", "EMA 20"])

    # Map time period to the corresponding interval
    interval_mapping = {
        "1d": "1m",
        "1wk": "30m",
        "1mo": "1d",
        "1y": "1wk",
        "max": "1wk"
    }

    # Update chart button and session state
    if st.sidebar.button("Update Chart"):
        st.session_state.update_chart = True
    else:
        if "update_chart" not in st.session_state:
            st.session_state.update_chart = False

    # Auto-refresh every 60 seconds
    st_autorefresh(interval=6000, key="real_time_data_refresh")

    if st.session_state.update_chart:
        data = fetch_stock_data(ticker, time_period, interval_mapping[time_period])
        data = process_data(data)
        if data.empty:
            st.warning(f"No data available for ticker: {ticker}")
        else:
            data = add_technical_indicators(data)
            last_close, change, pct_change, high, low, volume = calculate_metrics(data)
            if last_close is None:
                st.error("Insufficient data to display metrics.")
            else:
                st.metric(label=f"{company_name} Last Price", value=f"{last_close:.2f} INR",
                          delta=f"{change:.2f} ({pct_change:.2f}%)")
                col1, col2, col3 = st.columns(3)
                col1.metric("High", f"{high:.2f} INR" if high is not None else "N/A")
                col2.metric("Low", f"{low:.2f} INR" if low is not None else "N/A")
                col3.metric("Volume", f"{volume:,}" if volume is not None else "N/A")

                # Create the stock price chart
                fig = go.Figure()
                if chart_type == "Candlestick":
                    if all(col in data.columns for col in ['Open', 'High', 'Low', 'Close']):
                        fig.add_trace(go.Candlestick(x=data['Datetime'],
                                                     open=data['Open'],
                                                     high=data['High'],
                                                     low=data['Low'],
                                                     close=data['Close'],
                                                     name=ticker))
                    else:
                        st.error("Required columns for Candlestick chart are missing.")
                else:
                    if 'Close' in data.columns:
                        fig = px.line(data, x='Datetime', y='Close', title=f'{ticker} Price')
                    else:
                        st.error("'Close' column is missing in data.")
                for indicator in indicators:
                    if indicator == "SMA 20" and "SMA_20" in data.columns:
                        fig.add_trace(go.Scatter(x=data['Datetime'], y=data['SMA_20'],
                                                 mode='lines', name='SMA 20'))
                    elif indicator == "EMA 20" and "EMA_20" in data.columns:
                        fig.add_trace(go.Scatter(x=data['Datetime'], y=data['EMA_20'],
                                                 mode='lines', name='EMA 20'))
                fig.update_layout(
                    title=f'{ticker} {time_period.upper()} Chart',
                    xaxis_title='Time',
                    yaxis_title='Price (INR)',
                    xaxis_rangeslider_visible=True,
                    height=600
                )
                st.plotly_chart(fig, use_container_width=True)

                # Display historical and technical data
                st.subheader("Historical Data")
                display_cols = ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']
                available_cols = [col for col in display_cols if col in data.columns]
                st.dataframe(data[available_cols])

                st.subheader("Technical Indicators")
                tech_cols = ['Datetime', 'SMA_20', 'EMA_20']
                available_tech = [col for col in tech_cols if col in data.columns]
                st.dataframe(data[available_tech][40:])

    # Sidebar: Real-Time Stock Prices for selected symbols
    st.sidebar.header("Real-Time Stock Prices")
    stock_symbols = ["HDFC Bank", "ICICI Bank", "State Bank of India"]
    for symbol in stock_symbols:
        tick_sym = nifty_50_dict[symbol]
        rt_data = yf.download(tick_sym, period='1d', interval='1m')
        rt_data = process_data(rt_data)
        if rt_data.empty or 'Open' not in rt_data.columns:
            st.sidebar.write(f"Data for {symbol} is not available.")
        else:
            try:
                first_open = float(rt_data['Open'].iloc[0])
            except Exception as e:
                st.sidebar.write(f"Error processing open price for {symbol}: {e}")
                continue

            if pd.notna(first_open) and first_open != 0:
                last_price = float(rt_data['Close'].iloc[-1])
                change = last_price - first_open
                pct_change = (change / first_open) * 100
            else:
                last_price = float(rt_data['Close'].iloc[-1])
                change = 0
                pct_change = 0

            st.sidebar.metric(f"{symbol}", f"{last_price:.2f} INR",
                              f"{change:.2f} ({pct_change:.2f}%)")
    st.sidebar.subheader("About")
    st.sidebar.info(
        "This dashboard provides real-time and historical stock data with technical indicators. "
        "Data refreshes automatically every minute."
    )
    
elif app_mode == "Stock Forecast":
    st.title("Stock Forecasting")
    
    company_name = st.sidebar.selectbox("Select Company", list(nifty_50_dict.keys()))
    ticker_forecast = nifty_50_dict[company_name]
    forecast_option = st.sidebar.selectbox("Number of Days to Forecast", [3, 5, 10], index=0)
    period_options = st.sidebar.selectbox("Historical Data Period", ["1y", "2y", "5y"], index=0)

    run_button = st.sidebar.button("Run Forecast")

    if run_button:
        forecast_future = forecast_pct_change(ticker_forecast, forecast_days=forecast_option, period=period_options)
        
        if forecast_future is not None:
            display_forecast = forecast_future[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].rename(
                columns={'ds': 'Date', 'yhat': '% Change', 'yhat_lower': 'Lower Bound', 'yhat_upper': 'Upper Bound'}
            ).reset_index(drop=True)
            display_forecast.index += 1
            
            # Store the forecasted data in session state
            st.session_state["forecast_data"] = display_forecast
            st.session_state["forecast_plot"] = forecast_future  # Store raw forecast for plotting
            
    # Check if forecast data exists in session state before displaying
    if "forecast_data" in st.session_state:
        st.subheader(f"Forecasted Percentage Change for Next {forecast_option} Days")
        st.dataframe(st.session_state["forecast_data"])

        # Plot the stored forecast data
        fig = go.Figure()
        forecast_future = st.session_state["forecast_plot"]
        fig.add_trace(go.Scatter(
            x=forecast_future['ds'], y=forecast_future['yhat'],
            mode='lines+markers', name='Forecasted Pct Change',
            error_y=dict(
                type='data', symmetric=False,
                array=forecast_future['yhat_upper'] - forecast_future['yhat'],
                arrayminus=forecast_future['yhat'] - forecast_future['yhat_lower']
            )
        ))
        fig.update_layout(title=f"Forecast of {company_name} Percentage Change", xaxis_title="Date", yaxis_title="Percentage Change (%)")
        st.plotly_chart(fig)

    # **Keep "Get Suggestions" Separate to Avoid Page Refresh**
    if st.button("Get Suggestions"):
        with st.spinner("Fetching suggestions..."):
            ans = get_suggestions(ticker_forecast, period=period_options)
        st.subheader("A.I Suggestions:")
        st.write(ans)
        
