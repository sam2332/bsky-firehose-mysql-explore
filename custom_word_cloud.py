#!/usr/bin/env python3
"""
Interactive Word Cloud Generator
Customize your word art with different options
"""

import mysql.connector
import re
from collections import Counter
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import numpy as np
from PIL import Image
import os
import argparse

# Database configuration
MYSQL_CONFIG = {
    'host': 'mariadb',
    'database': 'bsky_db',
    'user': 'bsky_user',
    'password': 'bsky_password',
    'port': 3306
}

# Comprehensive stop words (same as before)
ENGLISH_STOP_WORDS = {
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
    'don', 'can', 'said', 'each', 'which', 'she', 'do', 'how', 'their', 'if', 
    'will', 'up', 'other', 'about', 'out', 'many', 'then', 'them', 'these', 'so', 
    'some', 'her', 'would', 'make', 'like', 'into', 'him', 'time', 'two', 'more', 
    'go', 'see', 'no', 'could', 'than', 'first', 'been', 'call', 'who', 'oil', 
    'sit', 'now', 'find', 'long', 'down', 'day', 'did', 'get', 'come', 'made', 
    'may', 'part', 'over', 'new', 'sound', 'take', 'only', 'little', 'work', 
    'know', 'place', 'year', 'live', 'me', 'back', 'give', 'most', 'very', 'after',
    'rt', 'via', 'cc', 'dm', 'pm', 'am', 'pm', 'lol', 'omg', 'wtf', 'tbh', 'imo', 
    'imho', 'fyi', 'btw', 'aka', 'asap', 'ttyl', 'brb', 'afk', 'irl', 'tl', 'dr',
    'http', 'https', 'www', 'com', 'org', 'net', 'bsky', 'social', 'at',
    '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '2024', '2025',
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

def get_posts_text(hours_ago=24, language='en', search_term=None):
    """Get post text from the database"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        if search_term:
            query = '''
                SELECT text FROM posts 
                WHERE created_at > DATE_SUB(NOW(), INTERVAL %s HOUR)
                AND (language = %s OR language IS NULL)
                AND text LIKE %s
                AND LENGTH(text) > 10
            '''
            cursor.execute(query, (hours_ago, language, f'%{search_term}%'))
        else:
            query = '''
                SELECT text FROM posts 
                WHERE created_at > DATE_SUB(NOW(), INTERVAL %s HOUR)
                AND (language = %s OR language IS NULL)
                AND LENGTH(text) > 10
                AND text NOT LIKE 'RT @%%'
            '''
            cursor.execute(query, (hours_ago, language))
        
        posts = cursor.fetchall()
        conn.close()
        
        return [post[0] for post in posts if post[0]]
        
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return []

def clean_text(text, min_word_length=3):
    """Clean and preprocess text"""
    text = text.lower()
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'#\w+', '', text)
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

def create_custom_word_cloud(text, args):
    """Create a customized word cloud"""
    
    # Custom stopwords
    stop_words = ENGLISH_STOP_WORDS.copy()
    if args.extra_stopwords:
        extra_words = set(word.strip().lower() for word in args.extra_stopwords.split(','))
        stop_words.update(extra_words)
    
    # WordCloud parameters
    wordcloud = WordCloud(
        width=args.width,
        height=args.height,
        max_words=args.max_words,
        background_color=args.background,
        colormap=args.colormap,
        stopwords=stop_words,
        relative_scaling=args.scaling,
        min_font_size=args.min_font,
        max_font_size=args.max_font,
        prefer_horizontal=args.horizontal,
        collocations=False
    ).generate(text)
    
    # Create and save plot
    plt.figure(figsize=(args.width/100, args.height/100))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    
    if args.title:
        plt.title(args.title, fontsize=20, fontweight='bold', pad=20)
    
    plt.tight_layout(pad=0)
    
    # Save the image
    output_file = args.output or f"custom_wordcloud_{args.colormap}_{args.background}.png"
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    
    if args.show:
        plt.show()
    else:
        plt.close()
    
    return output_file

def main():
    parser = argparse.ArgumentParser(description='Create custom word clouds from Bluesky posts')
    
    # Data options
    parser.add_argument('--hours', type=int, default=24, help='Hours of posts to analyze (default: 24)')
    parser.add_argument('--search', type=str, help='Only include posts containing this term')
    parser.add_argument('--language', type=str, default='en', help='Language filter (default: en)')
    
    # Visual options
    parser.add_argument('--width', type=int, default=1600, help='Image width (default: 1600)')
    parser.add_argument('--height', type=int, default=800, help='Image height (default: 800)')
    parser.add_argument('--max-words', type=int, default=200, help='Maximum words to show (default: 200)')
    parser.add_argument('--background', type=str, default='white', help='Background color (default: white)')
    parser.add_argument('--colormap', type=str, default='viridis', 
                       help='Color scheme: viridis, plasma, inferno, magma, rainbow, etc. (default: viridis)')
    
    # Font options
    parser.add_argument('--min-font', type=int, default=10, help='Minimum font size (default: 10)')
    parser.add_argument('--max-font', type=int, default=100, help='Maximum font size (default: 100)')
    parser.add_argument('--scaling', type=float, default=0.5, help='Font size scaling (default: 0.5)')
    parser.add_argument('--horizontal', type=float, default=0.7, help='Prefer horizontal text (0-1, default: 0.7)')
    
    # Content options
    parser.add_argument('--extra-stopwords', type=str, help='Additional stop words (comma-separated)')
    parser.add_argument('--title', type=str, help='Title for the word cloud')
    
    # Output options
    parser.add_argument('--output', type=str, help='Output filename')
    parser.add_argument('--show', action='store_true', help='Display the word cloud')
    
    args = parser.parse_args()
    
    print(f"🎨 Creating custom word cloud...")
    print(f"📊 Fetching posts from last {args.hours} hours...")
    
    # Get posts
    posts = get_posts_text(hours_ago=args.hours, language=args.language, search_term=args.search)
    
    if not posts:
        print("❌ No posts found with the specified criteria")
        return
    
    print(f"✅ Found {len(posts)} posts")
    
    # Clean text
    all_text = []
    for post in posts:
        cleaned = clean_text(post, min_word_length=3)  # Filter words < 3 chars
        if len(cleaned.strip()) > 5:
            all_text.append(cleaned)
    
    combined_text = ' '.join(all_text)
    
    if not combined_text.strip():
        print("❌ No meaningful text found after cleaning")
        return
    
    print(f"✅ Processing {len(combined_text.split())} words...")
    
    # Create word cloud
    output_file = create_custom_word_cloud(combined_text, args)
    
    print(f"🎉 Word cloud saved as: {output_file}")
    
    # Show top words
    words = combined_text.split()
    stop_words = ENGLISH_STOP_WORDS.copy()
    if args.extra_stopwords:
        extra_words = set(word.strip().lower() for word in args.extra_stopwords.split(','))
        stop_words.update(extra_words)
    
    word_freq = Counter(word for word in words if word not in stop_words and len(word) > 2)
    
    print(f"\n📈 Top 15 words in your word cloud:")
    for i, (word, count) in enumerate(word_freq.most_common(15), 1):
        print(f"   {i:2d}. {word:<15} ({count} times)")

if __name__ == "__main__":
    main()
