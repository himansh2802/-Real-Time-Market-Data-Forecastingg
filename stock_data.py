# stock_data.py

import pandas as pd
import yfinance as yf
import ta
import streamlit as st
from datetime import datetime, timedelta
import pytz

# Nifty 50 Company Name to Ticker Mapping
nifty_50_dict = {
    "Adani Ports and SEZ": "ADANIPORTS.NS",
    "Axis Bank": "AXISBANK.NS",
    "Asian Paints": "ASIANPAINT.NS",
    "Bajaj Auto": "BAJAJ-AUTO.NS",
    "Bajaj Finance": "BAJFINANCE.NS",
    "Bajaj Finserv": "BAJAJFINSV.NS",
    "Bandhan Bank": "BANDHANBNK.NS",
    "Bharti Airtel": "BHARTIARTL.NS",
    "BPCL": "BPCL.NS",
    "Cipla": "CIPLA.NS",
    "Divi's Laboratories": "DIVISLAB.NS",
    "Dr. Reddy's Laboratories": "DRREDDY.NS",
    "Eicher Motors": "EICHERMOT.NS",
    "Grasim Industries": "GRASIM.NS",
    "HCL Technologies": "HCLTECH.NS",
    "HDFC": "HDFC.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "HDFC Life Insurance": "HDFCLIFE.NS",
    "Hero MotoCorp": "HEROMOTOCO.NS",
    "Hindustan Unilever": "HINDUNILVR.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Indian Oil Corporation": "IOC.NS",
    "IndusInd Bank": "INDUSINDBK.NS",
    "ITC": "ITC.NS",
    "Kotak Mahindra Bank": "KOTAKBANK.NS",
    "Larsen & Toubro": "LT.NS",
    "Lupin": "LUPIN.NS",
    "Maruti Suzuki": "MARUTI.NS",
    "M&M": "M&M.NS",
    "Muthoot Finance": "MUTHOOTFIN.NS",
    "Nestlé India": "NESTLEIND.NS",
    "NTPC": "NTPC.NS",
    "Power Grid Corporation": "POWERGRID.NS",
    "Reliance Industries": "RELIANCE.NS",
    "Shree Cement": "SHREECEM.NS",
    "SBI Life Insurance": "SBILIFE.NS",
    "State Bank of India": "SBIN.NS",
    "Sun Pharmaceutical": "SUNPHARMA.NS",
    "Tata Consumer Products": "TATACONSUM.NS",
    "Tata Motors": "TATAMOTORS.NS",
    "Tata Steel": "TATASTEEL.NS",
    "Tech Mahindra": "TECHM.NS",
    "Titan": "TITAN.NS",
    "UltraTech Cement": "ULTRACEMCO.NS",
    "Wipro": "WIPRO.NS",
    "Zee Entertainment": "ZEEL.NS",
    "Zydus Lifesciences": "ZYDUSLIFE.NS"
}

@st.cache_data(ttl=60)
def fetch_stock_data(ticker, period, interval):
    """Fetch historical stock data from yfinance."""
    end_date = datetime.now()
    if period == '1wk':
        start_date = end_date - timedelta(days=7)
        data = yf.download(ticker, start=start_date, end=end_date, interval=interval)
    else:
        data = yf.download(ticker, period=period, interval=interval)
    return data

def process_data(data):
    """Process the DataFrame: adjust columns, timezone, and filter out missing data."""
    if data.empty:
        st.error("No data fetched for the given ticker.")
        return data

    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    else:
        new_columns = {col: col.split(',')[0] for col in data.columns if isinstance(col, str)}
        data.rename(columns=new_columns, inplace=True)

    if data.index.tzinfo is None:
        data.index = data.index.tz_localize('UTC')
    data.index = data.index.tz_convert('Asia/Kolkata')
    data.reset_index(inplace=True)

    if 'Date' in data.columns and 'Datetime' not in data.columns:
        data.rename(columns={'Date': 'Datetime'}, inplace=True)

    data = data.dropna(subset=['Close'])
    return data

def calculate_metrics(data):
    """Calculate key metrics (last close, change, percentage change, high, low, volume)."""
    if data.empty or 'Close' not in data.columns:
        return None, None, None, None, None, None
    last_close = data['Close'].iloc[-1]
    prev_close = data['Close'].iloc[0]
    change = last_close - prev_close
    pct_change = (change / prev_close) * 100 if prev_close != 0 else 0
    high = data['High'].max() if 'High' in data.columns else None
    low = data['Low'].min() if 'Low' in data.columns else None
    volume = data['Volume'].sum() if 'Volume' in data.columns else None
    return last_close, change, pct_change, high, low, volume

def add_technical_indicators(data):
    """Add 20-period SMA and EMA to the data."""
    if data.empty or 'Close' not in data.columns:
        st.warning("Data is empty or missing 'Close' column for technical indicators.")
        return data

    data = data.dropna(subset=['Close'])
    if len(data) < 20:
        st.warning("Not enough data to calculate SMA or EMA (need at least 20 data points).")
        return data

    data['SMA_20'] = ta.trend.sma_indicator(data['Close'], window=20)
    data['EMA_20'] = ta.trend.ema_indicator(data['Close'], window=20)
    return data
