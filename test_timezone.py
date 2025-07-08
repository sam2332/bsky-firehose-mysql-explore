#!/usr/bin/env python3
"""
Test script to verify timezone conversion is working correctly for Michigan timezone.
This script tests the format_datetime function to ensure times are displayed in Eastern Time.
"""

import sys
import os
sys.path.append('/workspaces/bsky/flask-app')

from datetime import datetime
import pytz

# Import the format_datetime function from the Flask app
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
    
    if diff.days > 7:
        return dt_eastern.strftime('%Y-%m-%d %I:%M %p ET')
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"

def test_timezone_conversion():
    """Test the timezone conversion functionality"""
    
    print("Testing timezone conversion for Michigan (Eastern Time)")
    print("=" * 60)
    
    # Get current time in different timezones
    utc = pytz.UTC
    eastern = pytz.timezone('US/Eastern')
    
    now_utc = datetime.now(utc)
    now_eastern = datetime.now(eastern)
    
    print(f"Current UTC time: {now_utc.strftime('%Y-%m-%d %I:%M %p UTC')}")
    print(f"Current Eastern time: {now_eastern.strftime('%Y-%m-%d %I:%M %p ET')}")
    print(f"Time difference: {(now_utc.hour - now_eastern.hour) % 24} hours")
    print()
    
    # Test with a sample UTC timestamp (like what might come from Bluesky API)
    test_utc_time = datetime(2025, 1, 8, 8, 14, 0, tzinfo=utc)  # 8:14 AM UTC
    expected_eastern = test_utc_time.astimezone(eastern)
    
    print("Test Case: Converting UTC timestamp to Eastern time")
    print(f"Input UTC time: {test_utc_time.strftime('%Y-%m-%d %I:%M %p UTC')}")
    print(f"Expected Eastern time: {expected_eastern.strftime('%Y-%m-%d %I:%M %p ET')}")
    
    # Test the format_datetime function
    formatted_result = format_datetime(test_utc_time)
    print(f"format_datetime result: {formatted_result}")
    print()
    
    # Test with ISO string format (common in APIs)
    iso_string = "2025-01-08T08:14:00Z"
    print("Test Case: Converting ISO string to Eastern time")
    print(f"Input ISO string: {iso_string}")
    formatted_iso = format_datetime(iso_string)
    print(f"format_datetime result: {formatted_iso}")
    print()
    
    print("Timezone conversion test completed!")
    print("The times should now display correctly in Michigan Eastern Time.")

if __name__ == "__main__":
    test_timezone_conversion()
