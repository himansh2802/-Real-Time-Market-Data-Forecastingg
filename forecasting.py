
import pandas as pd
import yfinance as yf
from prophet import Prophet
import streamlit as st
import matplotlib.pyplot as plt
import google.generativeai as genai
from PIL import Image
import requests
import io
import numpy as np
import base64
import os

@st.cache_data(ttl=3600)
def fetch_stock_data_daily(ticker, period="1y"):
    """Fetch daily stock data for the given ticker and period."""
    data = yf.download(ticker, period=period, interval="1d")
    if data.empty:
        st.error(f"No data fetched for ticker: {ticker}")
        return data

    # Ensure column names are simplified
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)
    else:
        new_columns = {col: col.split(',')[0] for col in data.columns if isinstance(col, str)}
        data.rename(columns=new_columns, inplace=True)

    data = data.dropna(subset=['Close'])
    data['Pct_Change'] = data['Close'].pct_change() * 100
    data.dropna(subset=['Pct_Change'], inplace=True)
    data.reset_index(inplace=True)
    return data

def forecast_pct_change(ticker, forecast_days=3, period="1y"):
    """Use Prophet to forecast future stock percentage change."""
    data = fetch_stock_data_daily(ticker, period)
    if data.empty:
        return None
    # Prepare data for Prophet (rename Date to ds and Pct_Change to y)
    df = data[['Date', 'Pct_Change']].rename(columns={'Date': 'ds', 'Pct_Change': 'y'})
    model = Prophet(daily_seasonality=True)
    model.fit(df)
    future = model.make_future_dataframe(periods=forecast_days)
    forecast = model.predict(future)
    forecast_future = forecast.tail(forecast_days)
    return forecast_future

def get_image(data, tick):
    """Generate a plot image showing historical percentage changes."""
    fig_mat, ax = plt.subplots(figsize=(10, 6))

    dates = np.array(data['Date'])
    pct_changes = np.array(data['Pct_Change'])
    ax.plot(dates, pct_changes, marker='o', linestyle='-')

    ax.set_title(f'Historical Percentage Changes for {tick}')
    ax.set_xlabel('Date')
    ax.set_ylabel('Percentage Change (%)')
    ax.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save the matplotlib figure to an in-memory PNG image.
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close(fig_mat)
    buf.seek(0)
    image_bytes = buf.read()
    return image_bytes

def get_suggestions(ticker, period="1y"):
    """Generate AI suggestions using the Gemini vision model."""
    data = fetch_stock_data_daily(ticker, period)
    data['Date'] = pd.to_datetime(data['Date'])
    if data.empty:
        return None

    # Generate the image and convert to a PIL Image
    image_bytes = get_image(data, ticker)
    image = Image.open(io.BytesIO(image_bytes))

    # Initialize the Gemini client
    api_key = os.getenv('API_KEY')  # Get the API key from environment variables
    if not api_key:
        st.error("API key not found. Please set the API_KEY environment variable.")
        return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')

    prompt = '''You are a seasoned financial analyst with over 15 years of experience in trading and technical analysis. You possess deep insights into market trends and the ability to interpret complex financial data, making you an expert at providing actionable trading suggestions based on chart analysis.
Your task is to analyze a provided chart that displays percentage change over time and offer trading suggestions. 
Analyze the stock chart and provide a buy/hold/sell recommendation

Present your findings in a clear, well-structured format suitable for sharing with other traders. Include an executive summary, detailed observations, and specific trading recommendations based on your analysis.
'''

    # Generate content using the image by passing the PIL Image directly
    try:
        response = model.generate_content(
            [prompt, image],
            stream=True
        )
        response.resolve()  # Wait for the response if necessary
        suggestion = response.text
    except Exception as e:
        st.error(f"Error generating suggestions: {e}")
        suggestion = None

    return suggestion
