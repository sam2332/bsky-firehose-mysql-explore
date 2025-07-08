#!/usr/bin/env python3
"""
Test the fixed format_datetime function
"""

import sys
import os
sys.path.append('/workspaces/bsky/flask-app')

from datetime import datetime, timedelta
import pytz

def format_datetime(dt) -> str:
    """Format datetime for display in Michigan timezone (Eastern Time)"""
    if not dt:
        return "Unknown"
    
    # Define Michigan timezone (Eastern Time)
    eastern = pytz.timezone('US/Eastern')
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except Exception:
            return dt
    
    # Convert to Michigan timezone if datetime has timezone info
    if dt.tzinfo:
        # Convert to Eastern time
        dt_eastern = dt.astimezone(eastern)
    else:
        # Assume UTC if no timezone info and convert to Eastern
        utc = pytz.UTC
        dt_utc = utc.localize(dt)
        dt_eastern = dt_utc.astimezone(eastern)
    
    # Calculate time difference using Eastern time
    now_eastern = datetime.now(eastern)
    diff = now_eastern - dt_eastern
    
    # Handle negative differences (future dates)
    if diff.total_seconds() < 0:
        return dt_eastern.strftime('%Y-%m-%d %I:%M %p ET')
    
    # Get total seconds for accurate calculations
    total_seconds = diff.total_seconds()
    
    if diff.days > 7:
        return dt_eastern.strftime('%Y-%m-%d %I:%M %p ET')
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif total_seconds > 3600:
        hours = int(total_seconds // 3600)
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif total_seconds > 60:
        minutes = int(total_seconds // 60)
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

def test_datetime_formatting():
    """Test various datetime scenarios"""
    
    eastern = pytz.timezone('US/Eastern')
    utc = pytz.UTC
    now_eastern = datetime.now(eastern)
    
    print("Testing format_datetime function")
    print("=" * 50)
    print(f"Current Eastern time: {now_eastern}")
    print()
    
    # Test cases
    test_cases = [
        # Just now
        (now_eastern - timedelta(seconds=30), "30 seconds ago"),
        
        # Minutes ago
        (now_eastern - timedelta(minutes=5), "5 minutes ago"),
        (now_eastern - timedelta(minutes=45), "45 minutes ago"),
        
        # Hours ago
        (now_eastern - timedelta(hours=2), "2 hours ago"),
        (now_eastern - timedelta(hours=12), "12 hours ago"),
        
        # Days ago
        (now_eastern - timedelta(days=1), "1 day ago"),
        (now_eastern - timedelta(days=3), "3 days ago"),
        (now_eastern - timedelta(days=7), "7 days ago"),
        
        # Over a week ago (should show date)
        (now_eastern - timedelta(days=10), "should show date"),
        (now_eastern - timedelta(days=180), "should show date"),
        
        # UTC timestamps (like from API)
        (datetime.now(utc) - timedelta(hours=1), "1 hour ago (from UTC)"),
        (datetime.now(utc) - timedelta(days=2), "2 days ago (from UTC)"),
    ]
    
    for test_dt, expected_type in test_cases:
        result = format_datetime(test_dt)
        print(f"Input: {test_dt}")
        print(f"Expected type: {expected_type}")
        print(f"Result: {result}")
        print("-" * 30)

if __name__ == "__main__":
    test_datetime_formatting()
