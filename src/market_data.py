"""
Market data module for fetching real-time S&P 500 data.
"""

import yfinance as yf
from datetime import datetime, timezone, timedelta
from typing import Optional


def get_realtime_sp500_data() -> dict:
    """
    Fetch current S&P 500 price and market context.
    
    Returns:
        dict with market snapshot data including:
        - sp500_price: Current price
        - sp500_daily_change: Daily change in dollars
        - sp500_daily_change_pct: Daily change in percentage
        - sp500_weekly_change_pct: 7-day change in percentage
        - sp500_50d_ma: 50-day moving average
        - sp500_distance_from_50d_ma_pct: Distance from 50d MA in percentage
        - market_status: open/closed/pre-market/after-hours
        - captured_at: Timestamp when data was captured
    """
    try:
        sp500 = yf.Ticker("^GSPC")
        
        # Get current price data
        info = sp500.info
        current_price = info.get("regularMarketPrice", 0)
        previous_close = info.get("regularMarketPreviousClose", current_price)
        
        # Calculate daily change
        daily_change = current_price - previous_close
        daily_change_pct = (daily_change / previous_close * 100) if previous_close > 0 else 0
        
        # Get historical data for weekly change and 50d MA
        hist = sp500.history(period="60d")
        
        # Weekly change (7 trading days ago)
        if len(hist) >= 7:
            week_ago_price = hist.iloc[-7]["Close"]
            weekly_change_pct = ((current_price - week_ago_price) / week_ago_price * 100)
        else:
            weekly_change_pct = 0
        
        # 50-day moving average
        if len(hist) >= 50:
            sp500_50d_ma = hist["Close"].tail(50).mean()
            distance_from_50d_ma_pct = ((current_price - sp500_50d_ma) / sp500_50d_ma * 100)
        else:
            sp500_50d_ma = hist["Close"].mean() if len(hist) > 0 else current_price
            distance_from_50d_ma_pct = 0
        
        # Determine market status
        market_status = _get_market_status(sp500)
        
        return {
            "sp500_price": round(current_price, 2),
            "sp500_daily_change": round(daily_change, 2),
            "sp500_daily_change_pct": round(daily_change_pct, 2),
            "sp500_weekly_change_pct": round(weekly_change_pct, 2),
            "sp500_50d_ma": round(sp500_50d_ma, 2),
            "sp500_distance_from_50d_ma_pct": round(distance_from_50d_ma_pct, 2),
            "market_status": market_status,
            "captured_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        print(f"Warning: Could not fetch market data: {e}")
        # Return empty/zero values if fetch fails
        return {
            "sp500_price": 0,
            "sp500_daily_change": 0,
            "sp500_daily_change_pct": 0,
            "sp500_weekly_change_pct": 0,
            "sp500_50d_ma": 0,
            "sp500_distance_from_50d_ma_pct": 0,
            "market_status": "unknown",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


def _get_market_status(ticker: yf.Ticker) -> str:
    """
    Determine current market status.
    
    Returns:
        str: 'open', 'closed', 'pre-market', or 'after-hours'
    """
    try:
        # Get current time in ET (market timezone)
        now_et = datetime.now(timezone.utc) - timedelta(hours=5)  # Approximate ET
        
        # Market hours: 9:30 AM - 4:00 PM ET, Mon-Fri
        hour = now_et.hour
        minute = now_et.minute
        weekday = now_et.weekday()  # 0=Monday, 6=Sunday
        
        # Weekend
        if weekday >= 5:
            return "closed"
        
        current_time = hour * 60 + minute
        
        # Pre-market: 4:00 AM - 9:30 AM ET
        if 240 <= current_time < 570:
            return "pre-market"
        
        # Regular hours: 9:30 AM - 4:00 PM ET
        if 570 <= current_time < 960:
            return "open"
        
        # After-hours: 4:00 PM - 8:00 PM ET
        if 960 <= current_time < 1200:
            return "after-hours"
        
        return "closed"
        
    except Exception:
        return "unknown"


def format_market_snapshot(market_data: dict) -> str:
    """
    Format market snapshot for display.
    
    Args:
        market_data: Market snapshot dict from get_realtime_sp500_data()
    
    Returns:
        str: Formatted market snapshot string
    """
    if market_data.get("sp500_price", 0) == 0:
        return "Market data unavailable"
    
    price = market_data["sp500_price"]
    daily_pct = market_data["sp500_daily_change_pct"]
    weekly_pct = market_data["sp500_weekly_change_pct"]
    ma_distance = market_data["sp500_distance_from_50d_ma_pct"]
    status = market_data["market_status"]
    
    return (
        f"S&P 500: ${price:,.2f} "
        f"({daily_pct:+.2f}% today, {weekly_pct:+.2f}% this week) "
        f"| vs 50d MA: {ma_distance:+.2f}% | {status}"
    )
