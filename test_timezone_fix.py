#!/usr/bin/env python3
"""
Test script to verify timezone conversion is working correctly for Michigan (Eastern Time)
"""
from datetime import datetime
import pytz

def utc_to_eastern(dt):
    """Convert UTC datetime to Eastern Time"""
    if not dt:
        return None
    
    # Define timezones
    utc = pytz.timezone('UTC')
    eastern = pytz.timezone('US/Eastern')
    
    # If datetime is naive, assume it's UTC
    if dt.tzinfo is None:
        dt = utc.localize(dt)
    
    # Convert to Eastern Time
    return dt.astimezone(eastern)

# Test with current UTC time
utc_now = datetime.utcnow()
eastern_now = utc_to_eastern(utc_now)

print("Timezone Conversion Test")
print("========================")
print(f"UTC Time:     {utc_now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
print(f"Eastern Time: {eastern_now.strftime('%Y-%m-%d %H:%M:%S %Z')} (Michigan)")
print(f"Time Difference: {(utc_now.hour - eastern_now.hour) % 24} hours")

# Test with a specific time to verify the conversion
test_utc = datetime(2025, 7, 8, 6, 15, 0)  # 6:15 AM UTC
test_eastern = utc_to_eastern(test_utc)

print("\nSpecific Test Case:")
print(f"6:15 AM UTC = {test_eastern.strftime('%I:%M %p %Z')} (should be around 1:15-2:15 AM EDT)")

# Check if we're in daylight saving time
is_dst = eastern_now.dst() != datetime.timedelta(0)
print(f"\nDaylight Saving Time: {'Yes' if is_dst else 'No'}")
print(f"Timezone Abbreviation: {eastern_now.strftime('%Z')}")
