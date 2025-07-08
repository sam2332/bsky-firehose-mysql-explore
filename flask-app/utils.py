"""
Utility functions and constants for the Flask application
"""

from datetime import datetime
import pytz

# Political keyword phrases for analysis (more contextual than single words)
RIGHT_WING_KEYWORDS = [
    # Trump & MAGA movement
    "make america great again", "maga", "trump 2024", "america first", 
    "drain the swamp", "deep state conspiracy", "stop the steal", "fake news media",
    "mainstream media lies", "liberal media bias", "election was stolen",
    
    # Conservative values & religion
    "traditional family values", "christian values", "religious freedom", "moral decay",
    "defend the constitution", "founding fathers intended", "constitutional rights",
    "god and country", "prayer in schools", "christian nation",
    
    # Gun rights
    "second amendment rights", "shall not be infringed", "gun grabbers", 
    "defend 2a", "right to bear arms", "good guy with gun", "constitutional carry",
    "gun control doesn't work", "criminals don't follow laws",
    
    # Immigration & border
    "secure the border", "illegal aliens", "build the wall", "mass deportation",
    "border crisis", "invasion at border", "merit based immigration",
    "chain migration", "sanctuary cities dangerous", "america first immigration",
    
    # Economic conservatism
    "free market capitalism", "small government", "lower taxes", "government overreach",
    "fiscal responsibility", "balanced budget", "job creators", "reduce regulations",
    "socialist policies", "government handouts", "welfare state",
    
    # Anti-left sentiments
    "woke ideology", "cancel culture", "virtue signaling", "identity politics",
    "cultural marxism", "critical race theory", "grooming children", "parental rights",
    "gender ideology", "biological reality", "protect our children", "indoctrination",
    
    # Law enforcement & military
    "back the blue", "blue lives matter", "law and order", "defund police insane",
    "support our troops", "strong military", "peace through strength",
    "thin blue line", "law enforcement heroes",
    
    # Nationalism & sovereignty
    "america first", "national sovereignty", "globalist agenda", "new world order",
    "drain the swamp", "deep state", "patriotic americans", "real americans",
    "silent majority", "forgotten americans", "common sense conservative"
]

LEFT_WING_KEYWORDS = [
    # Social justice & civil rights
    "social justice", "racial justice", "systemic racism", "black lives matter",
    "police brutality", "criminal justice reform", "prison abolition", 
    "defund the police", "restorative justice", "racial equity",
    
    # LGBTQ+ rights
    "lgbtq rights", "transgender rights", "marriage equality", "gender affirming care",
    "conversion therapy ban", "pride month", "love is love", "trans rights human rights",
    "protect trans kids", "drag queen story hour",
    
    # Women's rights & reproductive freedom
    "reproductive rights", "bodily autonomy", "abortion access", "planned parenthood",
    "my body my choice", "reproductive freedom", "women's rights", "gender equality",
    "pay gap", "glass ceiling", "reproductive justice",
    
    # Climate & environment
    "climate change real", "climate crisis", "green new deal", "renewable energy",
    "fossil fuel industry", "environmental justice", "carbon emissions", 
    "climate action now", "save the planet", "sustainable future",
    
    # Economic justice
    "wealth inequality", "income inequality", "tax the rich", "billionaire class",
    "living wage", "minimum wage increase", "workers rights", "union strong",
    "medicare for all", "universal healthcare", "student debt forgiveness",
    "affordable housing", "rent control", "universal basic income",
    
    # Progressive politics
    "democratic socialism", "progressive agenda", "fight for justice",
    "power to the people", "grassroots movement", "political revolution",
    "anti capitalism", "corporate greed", "wall street corruption",
    
    # Immigration & refugee rights
    "immigration reform", "pathway to citizenship", "dreamers deserve", 
    "refugee rights", "family separation", "kids in cages", "sanctuary cities",
    "no human is illegal", "border patrol abuse",
    
    # Anti-establishment
    "eat the rich", "abolish ice", "abolish prisons", "defund military",
    "corporate accountability", "big pharma greed", "healthcare human right",
    "housing human right", "food justice", "water is life",
    
    # International & peace
    "anti war", "military industrial complex", "stop bombing", "peace not war",
    "human rights violations", "international law", "war crimes", 
    "indigenous rights", "land back", "decolonize", "global solidarity",
    
    # Modern progressive terms
    "intersectional feminism", "check your privilege", "systemic oppression",
    "mutual aid", "community care", "harm reduction", "prison industrial complex",
    "disability justice", "neurodiversity", "accessibility matters"
]

STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
    'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
    'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must',
    'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
    'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'its', 'our',
    'their', 'mine', 'yours', 'hers', 'ours', 'theirs', 'what', 'which', 'who',
    'whom', 'whose', 'where', 'when', 'why', 'how', 'all', 'any', 'both', 'each',
    'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only',
    'own', 'same', 'so', 'than', 'too', 'very', 'can', 'just', 'now', 'get', 'like'
}


def format_post_text(text: str, max_length: int = 200) -> str:
    """Format post text for display"""
    if not text:
        return ""
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length] + "..."
    
    return text


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


def format_datetime(dt) -> str:
    """Format datetime for display in Michigan timezone (Eastern Time)"""
    if not dt:
        return "Unknown"
    
    # Define Michigan timezone (Eastern Time)
    eastern = pytz.timezone('US/Eastern')
    
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except ValueError:
            return dt
    
    # Convert to Michigan timezone if datetime has timezone info
    if dt.tzinfo:
        # Convert to Eastern time
        dt_eastern = dt.astimezone(eastern)
    else:
        # Assume UTC if no timezone info and convert to Eastern
        utc = pytz.timezone('UTC')
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
        return f"{round(total_seconds)} seconds ago"


def detect_political_phrases(text):
    """Detect political phrases in text and return matches - optimized version"""
    if not text:
        return {'right_wing': [], 'left_wing': [], 'total_score': 0}
    
    text_lower = text.lower()
    detected = {'right_wing': [], 'left_wing': [], 'total_score': 0}
    
    # Use only key phrases for faster detection
    key_right_phrases = [
        "maga", "trump", "america first", "gun rights", "border security",
        "traditional values", "deep state", "fake news"
    ]
    
    key_left_phrases = [
        "social justice", "climate change", "black lives matter", "lgbtq",
        "medicare for all", "wealth inequality", "defund police"
    ]
    
    # Check for right-wing phrases (faster lookup)
    for phrase in key_right_phrases:
        if phrase in text_lower:
            detected['right_wing'].append(phrase)
            detected['total_score'] += 1
    
    # Check for left-wing phrases (faster lookup)
    for phrase in key_left_phrases:
        if phrase in text_lower:
            detected['left_wing'].append(phrase)
            detected['total_score'] -= 1  # Negative score for left-wing
    
    return detected
