#!/usr/bin/env python3
"""
Word Cloud Generator for Bluesky Posts
Creates beautiful word art from collected posts
"""

import mysql.connector
import re
from collections import Counter
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import numpy as np
from PIL import Image
import os

# Database configuration
MYSQL_CONFIG = {
    'host': 'mariadb',
    'database': 'bsky_db',
    'user': 'bsky_user',
    'password': 'bsky_password',
    'port': 3306
}

# Comprehensive English stop words
ENGLISH_STOP_WORDS = {
    # Articles, pronouns, prepositions
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he', 
    'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'were', 
    'will', 'with', 'the', 'this', 'but', 'they', 'have', 'had', 'what', 'said', 
    'each', 'which', 'she', 'do', 'how', 'their', 'if', 'up', 'out', 'many', 
    'then', 'them', 'these', 'so', 'some', 'her', 'would', 'make', 'like', 'into', 
    'him', 'time', 'two', 'more', 'very', 'when', 'come', 'may', 'say', 'get', 
    'use', 'your', 'way', 'about', 'than', 'first', 'been', 'call', 'who', 'oil', 
    'sit', 'now', 'find', 'long', 'down', 'day', 'did', 'get', 'come', 'made', 
    'may', 'part', 'over', 'new', 'sound', 'take', 'only', 'little', 'work', 
    'know', 'place', 'year', 'live', 'me', 'back', 'give', 'most', 'very', 'after', 
    'thing', 'our', 'just', 'name', 'good', 'sentence', 'man', 'think', 'say', 
    'great', 'where', 'help', 'through', 'much', 'before', 'line', 'right', 'too', 
    'mean', 'old', 'any', 'same', 'tell', 'boy', 'follow', 'came', 'want', 'show', 
    'also', 'around', 'form', 'three', 'small', 'set', 'put', 'end', 'why', 'again', 
    'turn', 'here', 'off', 'went', 'old', 'number', 'no', 'way', 'could', 'people', 
    'my', 'than', 'first', 'water', 'been', 'call', 'who', 'its', 'now', 'find', 
    'long', 'down', 'day', 'did', 'get', 'come', 'made', 'may', 'part',
    
    # Common contractions and informal words
    'don', 'can', 'said', 'each', 'which', 'she', 'do', 'how', 'their', 'if', 
    'will', 'up', 'other', 'about', 'out', 'many', 'then', 'them', 'these', 'so', 
    'some', 'her', 'would', 'make', 'like', 'into', 'him', 'time', 'two', 'more', 
    'go', 'see', 'no', 'could', 'than', 'first', 'been', 'call', 'who', 'oil', 
    'sit', 'now', 'find', 'long', 'down', 'day', 'did', 'get', 'come', 'made', 
    'may', 'part', 'over', 'new', 'sound', 'take', 'only', 'little', 'work', 
    'know', 'place', 'year', 'live', 'me', 'back', 'give', 'most', 'very', 'after',
    
    # Social media specific
    'rt', 'via', 'cc', 'dm', 'pm', 'am', 'pm', 'lol', 'omg', 'wtf', 'tbh', 'imo', 
    'imho', 'fyi', 'btw', 'aka', 'asap', 'ttyl', 'brb', 'afk', 'irl', 'tl', 'dr',
    
    # URLs and handles
    'http', 'https', 'www', 'com', 'org', 'net', 'bsky', 'social', 'at',
    
    # Numbers and dates
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '2024', '2025',
    
    # Common words that don't add meaning
    'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
    'really', 'actually', 'literally', 'basically', 'totally', 'definitely', 
    'probably', 'maybe', 'perhaps', 'seems', 'looks', 'feels', 'sounds',
    'going', 'coming', 'getting', 'being', 'having', 'doing', 'saying', 'looking',
    'trying', 'making', 'taking', 'giving', 'working', 'playing', 'thinking',
    'something', 'someone', 'somewhere', 'somehow', 'sometimes', 'anything', 
    'anyone', 'anywhere', 'anytime', 'everything', 'everyone', 'everywhere',
    'nothing', 'nobody', 'nowhere', 'never', 'always', 'often', 'usually',
    'sometimes', 'rarely', 'seldom', 'once', 'twice', 'again', 'still', 'yet',
    'already', 'soon', 'later', 'before', 'after', 'during', 'while', 'since',
    'until', 'unless', 'although', 'though', 'however', 'therefore', 'because',
    'since', 'while', 'when', 'where', 'why', 'how', 'what', 'which', 'who',
    'whom', 'whose', 'that', 'this', 'these', 'those', 'here', 'there', 'where',
    'yes', 'no', 'ok', 'okay', 'well', 'oh', 'ah', 'um', 'uh', 'er', 'hmm'
}

def get_posts_text(hours_ago=1, language='en', min_length=10):
    """Get post text from the database"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Get posts from the last N hours
        query = '''
            SELECT text FROM posts 
            WHERE created_at > DATE_SUB(NOW(), INTERVAL %s HOUR)
            AND (language = %s OR language IS NULL)
            AND LENGTH(text) > %s
            AND text NOT LIKE 'RT @%%'
            AND text NOT LIKE '@%%'
        '''
        
        cursor.execute(query, (hours_ago, language, min_length))
        posts = cursor.fetchall()
        conn.close()
        
        return [post[0] for post in posts if post[0]]
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return []

def clean_text(text, min_word_length=3):
    """Clean and preprocess text"""
    # Convert to lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove mentions and hashtags
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#\w+', '', text)
    
    # Remove special characters but keep spaces
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Split into words, filter by length and remove stop words, then rejoin
    words = text.split()
    filtered_words = [
        word for word in words
        if len(word) >= min_word_length
        and word not in ENGLISH_STOP_WORDS
        and not word.isdigit()  # Remove pure numbers
    ]
    
    return ' '.join(filtered_words)


def create_word_cloud(text, title="Bluesky Word Cloud", width=1600, 
                      height=800, max_words=20, background_color='white', 
                      colormap='viridis', mask_image=None):
    """Create a word cloud from text"""
    
    # Create WordCloud object
    wordcloud_params = {
        'width': width,
        'height': height,
        'max_words': max_words,
        'background_color': background_color,
        'colormap': colormap,
        'stopwords': ENGLISH_STOP_WORDS,
        'relative_scaling': 0.5,
        'min_font_size': 10,
        'max_font_size': 100,
        'prefer_horizontal': 0.7,
        'collocations': False
    }
    
    # Add mask if provided
    if mask_image and os.path.exists(mask_image):
        try:
            mask = np.array(Image.open(mask_image))
            wordcloud_params['mask'] = mask
            wordcloud_params['background_color'] = None
            wordcloud_params['mode'] = 'RGBA'
        except Exception as e:
            print(f"Warning: Could not load mask image {mask_image}: {e}")
    
    wordcloud = WordCloud(**wordcloud_params)
    
    # Generate word cloud
    wordcloud.generate(text)
    
    # Create figure
    plt.figure(figsize=(20, 10))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title(title, fontsize=20, fontweight='bold', pad=20)
    plt.tight_layout(pad=0)
    
    return wordcloud, plt

def create_multiple_word_clouds(text_data, output_dir='word_clouds'):
    """Create multiple word cloud variations"""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Different color schemes
    color_schemes = [
        ('viridis', 'Viridis (Blue-Green)'),
        ('plasma', 'Plasma (Purple-Pink)'),
        ('inferno', 'Inferno (Dark-Orange)'),
        ('magma', 'Magma (Dark-Purple)'),
        ('cividis', 'Cividis (Blue-Yellow)'),
        ('tab10', 'Tab10 (Categorical)'),
        ('Set3', 'Set3 (Pastel)'),
        ('rainbow', 'Rainbow')
    ]
    
    # Different background colors
    backgrounds = [
        ('white', 'White Background'),
        ('black', 'Black Background'),
        ('navy', 'Navy Background'),
        ('darkslategray', 'Dark Slate Gray')
    ]
    
    created_files = []
    
    # Create standard word clouds
    for colormap, color_name in color_schemes[:4]:  # Limit to 4 to avoid too many files
        for bg_color, bg_name in backgrounds[:2]:  # Limit to 2 backgrounds
            filename = f"{output_dir}/wordcloud_{colormap}_{bg_color}.png"
            title = f"Bluesky Posts - {color_name} on {bg_name}"
            
            wordcloud, plt_obj = create_word_cloud(
                text_data, 
                title=title,
                colormap=colormap,
                background_color=bg_color,
                width=1600,
                height=800
            )
            
            plt_obj.savefig(filename, dpi=300, bbox_inches='tight', 
                           facecolor='white' if bg_color != 'white' else None)
            plt_obj.close()
            created_files.append(filename)
            print(f"✅ Created: {filename}")
    
    # Create a large high-resolution version
    filename = f"{output_dir}/wordcloud_large_hires.png"
    wordcloud, plt_obj = create_word_cloud(
        text_data,
        title="Bluesky Posts Word Cloud - High Resolution",
        width=3200,
        height=1600,
        max_words=300,
        colormap='viridis'
    )
    plt_obj.savefig(filename, dpi=300, bbox_inches='tight')
    plt_obj.close()
    created_files.append(filename)
    print(f"✅ Created high-res: {filename}")
    
    return created_files

def main():
    """Main function"""
    print("🎨 Bluesky Word Cloud Generator")
    print("=" * 50)
    
    # Get posts from database
    print("📊 Fetching posts from database...")
    posts = get_posts_text(hours_ago=24, language='en', min_length=10)
    
    if not posts:
        print("❌ No posts found in database")
        return
    
    print(f"✅ Found {len(posts)} posts")
    
    # Clean and combine all text
    print("🧹 Cleaning text...")
    all_text = []
    for post in posts:
        cleaned = clean_text(post, min_word_length=3)  # Filter words < 3 chars
        if len(cleaned.strip()) > 5:  # Only include posts with meaningful content
            all_text.append(cleaned)
    
    combined_text = ' '.join(all_text)
    
    if not combined_text.strip():
        print("❌ No meaningful text found after cleaning")
        return
    
    print(f"✅ Processed {len(all_text)} posts with {len(combined_text.split())} total words")
    
    # Create word clouds
    print("🎨 Creating word clouds...")
    created_files = create_multiple_word_clouds(combined_text)
    
    print(f"\n🎉 Successfully created {len(created_files)} word cloud files!")
    print("\n📁 Created files:")
    for file in created_files:
        print(f"   {file}")
    
    # Show word frequency stats
    print("\n📈 Top 20 most frequent words (after filtering):")
    words = combined_text.split()
    word_freq = Counter(words)  # Words are already filtered in clean_text
    
    for i, (word, count) in enumerate(word_freq.most_common(20), 1):
        print(f"   {i:2d}. {word:<15} ({count} times)")

if __name__ == "__main__":
    main()
