from flask import render_template
from utils import detect_political_phrases
def register_routes(app):
    
    @app.route('/analytics')
    def analytics():
        """Analytics dashboard page"""
        return render_template('analytics.html')

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
