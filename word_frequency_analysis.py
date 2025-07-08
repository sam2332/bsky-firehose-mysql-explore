#!/usr/bin/env python3
"""
Word Frequency Analysis for Bluesky Posts
Generates word frequency charts ignoring stop words
"""

import mysql.connector
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import re
import string
from typing import List, Dict, Tuple
import pandas as pd

# Database configuration
MYSQL_CONFIG = {
    'host': 'mariadb',
    'database': 'bsky_db',
    'user': 'bsky_user',
    'password': 'bsky_password',
    'port': 3306
}

# Common stop words in multiple languages
STOP_WORDS = {
    'english': {
        # Articles and determiners
        'the', 'a', 'an', 'all', 'any', 'both', 'each', 'every', 'few', 'many', 'more', 
        'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same',
        
        # Conjunctions
        'and', 'or', 'but', 'if', 'because', 'as', 'until', 'while', 'although', 'though',
        'unless', 'since', 'whether',
        
        # Prepositions
        'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'up', 'about', 'into',
        'through', 'during', 'before', 'after', 'above', 'below', 'between', 'among',
        'under', 'over', 'across', 'around', 'behind', 'beneath', 'beside', 'beyond',
        'inside', 'outside', 'toward', 'towards', 'upon', 'near', 'next', 'per', 'via',
        'within', 'without',
        
        # Pronouns
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
        'my', 'your', 'his', 'hers', 'its', 'our', 'their', 'myself', 'yourself',
        'himself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves',
        
        # Question words
        'what', 'which', 'who', 'whom', 'whose', 'when', 'where', 'why', 'how',
        
        # Demonstratives
        'this', 'that', 'these', 'those',
        
        # Verbs (common auxiliary and linking verbs)
        'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 
        'having', 'do', 'does', 'did', 'doing', 'will', 'would', 'could', 'should', 
        'may', 'might', 'must', 'can', 'shall', 'ought',
        
        # Contractions and negations
        'cant', 'wont', 'dont', 'isnt', 'arent', 'wasnt', 'werent', 'hasnt', 'havent',
        'hadnt', 'doesnt', 'didnt', 'wouldnt', 'couldnt', 'shouldnt', 'mightnt', 'mustnt',
        "don't", "won't", "isn't", "aren't", "wasn't", "weren't", "hasn't", "haven't",
        "hadn't", "doesn't", "didn't", "wouldn't", "couldn't", "shouldn't", "mightn't",
        "mustn't", "can't", "you're", "you've", "you'll", "you'd", "she's", "he's",
        "it's", "we're", "we've", "we'll", "we'd", "they're", "they've", "they'll",
        "they'd", "that's", "that'll", "there's", "there'll", "here's",
        
        # Common adverbs
        'so', 'than', 'too', 'very', 'just', 'now', 'here', 'there', 'then', 'once',
        'again', 'further', 'also', 'even', 'well', 'really', 'quite', 'rather',
        'pretty', 'still', 'yet', 'already', 'always', 'never', 'sometimes', 'often',
        'usually', 'maybe', 'perhaps', 'probably', 'definitely', 'certainly', 'sure',
        'actually', 'basically', 'literally', 'totally', 'completely', 'absolutely',
        'exactly', 'especially', 'particularly', 'generally', 'specifically', 'likely',
        'unlikely', 'possibly',
        
        # Common social media words
        'get', 'got', 'go', 'going', 'want', 'need', 'know', 'think', 'see', 'look',
        'feel', 'make', 'take', 'come', 'give', 'like', 'back', 'first', 'last',
        'good', 'bad', 'new', 'old', 'right', 'wrong', 'long', 'short', 'big', 'small',
        'high', 'low', 'much', 'little', 'enough', 'lot', 'lots', 'kind', 'sort', 'type',
        'thing', 'things', 'stuff', 'people', 'person', 'man', 'woman', 'guy', 'guys',
        'girl', 'girls', 'someone', 'something', 'somewhere', 'somehow', 'anyone',
        'everyone', 'nobody', 'nothing', 'anything', 'everything',
        
        # Time references
        'time', 'today', 'yesterday', 'tomorrow', 'day', 'days', 'week', 'weeks',
        'month', 'months', 'year', 'years', 'way', 'morning', 'afternoon', 'evening',
        'night', 'am', 'pm',
        
        # Platform specific
        'bsky', 'bluesky', 'social', 'www', 'http', 'https', 'com', 'org', 'net',
        'post', 'posts', 'tweet', 'tweets', 'share', 'shares', 'follow', 'follows',
        'follower', 'followers', 'user', 'users', 'account', 'accounts', 'out',
        
        # Numbers and quantifiers
        'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
        'eleven', 'twelve', 'twenty', 'thirty', 'forty', 'fifty', 'hundred', 'thousand',
        'million', 'billion', 'first', 'second', 'third',
        
        # Common interjections and filler words
        'oh', 'ah', 'eh', 'um', 'uh', 'hmm', 'yeah', 'yes', 'yep', 'no', 'nope', 'ok',
        'okay', 'thanks', 'thank', 'please', 'sorry', 'excuse', 'hello', 'hi', 'hey',
        'bye', 'goodbye', 'wow', 'omg', 'lol', 'lmao', 'haha', 'hehe',
        
        # Size and comparison
        'great', 'little', 'different', 'large', 'next', 'early', 'young', 'important',
        'public', 'same', 'able', 'better', 'best', 'worse', 'worst',
        
        # Social media artifacts
        'rt', 'via', 'amp', 'don', 'doesn', 'didn', 'won', 'wouldn', 'couldn', 'shouldn',
        'hasn', 'haven', 'hadn', 'isn', 'aren', 'wasn', 'weren',
        
        # Single letters (often artifacts)
        'a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p',
        'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z'
    },
    'portuguese': {
        'o', 'a', 'os', 'as', 'um', 'uma', 'uns', 'umas', 'de', 'do', 'da', 'dos', 'das',
        'em', 'no', 'na', 'nos', 'nas', 'por', 'para', 'com', 'sem', 'sob', 'sobre',
        'e', 'ou', 'mas', 'que', 'se', 'como', 'quando', 'onde', 'porque', 'eu', 'tu',
        'ele', 'ela', 'nós', 'vós', 'eles', 'elas', 'me', 'te', 'lhe', 'nos', 'vos',
        'lhes', 'meu', 'minha', 'meus', 'minhas', 'teu', 'tua', 'teus', 'tuas', 'seu',
        'sua', 'seus', 'suas', 'nosso', 'nossa', 'nossos', 'nossas', 'vosso', 'vossa',
        'vossos', 'vossas', 'este', 'esta', 'estes', 'estas', 'esse', 'essa', 'esses',
        'essas', 'aquele', 'aquela', 'aqueles', 'aquelas', 'isto', 'isso', 'aquilo',
        'ser', 'estar', 'ter', 'haver', 'fazer', 'dizer', 'ir', 'ver', 'dar', 'saber',
        'querer', 'poder', 'vir', 'ficar', 'dever', 'falar', 'pôr', 'trazer', 'chegar',
        'pensar', 'deixar', 'encontrar', 'parecer', 'usar', 'trabalhar', 'começar',
        'não', 'sim', 'bem', 'mal', 'muito', 'pouco', 'mais', 'menos', 'tanto', 'quanto',
        'tão', 'assim', 'aqui', 'ali', 'lá', 'aí', 'já', 'ainda', 'sempre', 'nunca',
        'hoje', 'ontem', 'amanhã', 'agora', 'depois', 'antes', 'então', 'talvez'
    },
    'japanese': {
        'の', 'に', 'は', 'を', 'た', 'が', 'で', 'て', 'と', 'し', 'れ', 'さ', 'ある',
        'いる', 'する', 'です', 'ます', 'だっ', 'でし', 'ない', 'なっ', 'この', 'その',
        'あの', 'どの', 'ここ', 'そこ', 'あそこ', 'どこ', 'これ', 'それ', 'あれ', 'どれ',
        '私', '僕', '俺', '君', 'あなた', '彼', '彼女', '我々', '彼ら', '彼女ら'
    }
}

# Combine all stop words
ALL_STOP_WORDS = set()
for lang_stops in STOP_WORDS.values():
    ALL_STOP_WORDS.update(lang_stops)


def clean_text(text: str) -> List[str]:
    """Clean and tokenize text, removing stop words and punctuation"""
    if not text:
        return []
    
    # Convert to lowercase
    text = text.lower()
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove mentions (@username)
    text = re.sub(r'@\w+', '', text)
    
    # Remove hashtags (but keep the text after #)
    text = re.sub(r'#(\w+)', r'\1', text)
    
    # Remove punctuation and numbers
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\d+', '', text)
    
    # Split into words
    words = text.split()
    
    # Filter out stop words and short words
    filtered_words = [
        word for word in words 
        if len(word) > 2 and word not in ALL_STOP_WORDS
    ]
    
    return filtered_words


def get_posts_data(language_filter: str = None, limit: int = None) -> List[str]:
    """Fetch posts from database"""
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        query = "SELECT text FROM posts WHERE text IS NOT NULL"
        params = []
        
        if language_filter:
            query += " AND language = %s"
            params.append(language_filter)
        
        query += " ORDER BY created_at DESC"
        
        if limit:
            query += " LIMIT %s"
            params.append(limit)
        
        cursor.execute(query, params)
        posts = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return posts
    except mysql.connector.Error as e:
        print(f"Database error: {e}")
        return []


def generate_word_frequency(posts: List[str], top_n: int = 30) -> Counter:
    """Generate word frequency from posts"""
    all_words = []
    
    for post in posts:
        words = clean_text(post)
        all_words.extend(words)
    
    return Counter(all_words).most_common(top_n)


def create_frequency_chart(word_freq: List[Tuple[str, int]], title: str = "Word Frequency Analysis"):
    """Create and display word frequency chart"""
    if not word_freq:
        print("No words to display")
        return
    
    # Prepare data
    words, counts = zip(*word_freq)
    
    # Create DataFrame for easier plotting
    df = pd.DataFrame({'word': words, 'count': counts})
    
    # Set up the plot style
    plt.style.use('seaborn-v0_8')
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Create horizontal bar chart
    bars = ax.barh(range(len(words)), counts, color='skyblue', edgecolor='navy', alpha=0.7)
    
    # Customize the chart
    ax.set_yticks(range(len(words)))
    ax.set_yticklabels(words)
    ax.set_xlabel('Frequency', fontsize=12, fontweight='bold')
    ax.set_ylabel('Words', fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
    
    # Add value labels on bars
    for i, (word, count) in enumerate(word_freq):
        ax.text(count + max(counts) * 0.01, i, str(count), 
                va='center', fontweight='bold', fontsize=10)
    
    # Invert y-axis to show highest frequency at top
    ax.invert_yaxis()
    
    # Add grid
    ax.grid(axis='x', alpha=0.3, linestyle='--')
    
    # Tight layout
    plt.tight_layout()
    
    # Save the chart
    filename = f"word_frequency_{title.lower().replace(' ', '_')}.png"
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    print(f"Chart saved as: {filename}")
    
    # Show the chart
    plt.show()


def print_stats(posts: List[str], word_freq: List[Tuple[str, int]]):
    """Print analysis statistics"""
    total_words = sum(len(clean_text(post)) for post in posts)
    unique_words = len(set(word for post in posts for word in clean_text(post)))
    
    print(f"\n📊 Analysis Statistics:")
    print(f"   Total posts analyzed: {len(posts):,}")
    print(f"   Total words (after cleaning): {total_words:,}")
    print(f"   Unique words: {unique_words:,}")
    print(f"   Top {len(word_freq)} most frequent words:")
    
    for i, (word, count) in enumerate(word_freq[:10], 1):
        print(f"   {i:2d}. {word:<15} ({count:,} times)")


def main():
    """Main function"""
    print("🔤 Bluesky Word Frequency Analysis")
    print("=" * 50)
    
    # Get user preferences
    print("\nOptions:")
    print("1. All posts")
    print("2. English posts only")
    print("3. Portuguese posts only")
    print("4. Japanese posts only")
    print("5. Recent posts only (last 1000)")
    
    choice = input("\nSelect option (1-5, default=1): ").strip() or "1"
    
    # Configure based on choice
    language_filter = None
    limit = None
    title_suffix = ""
    
    if choice == "2":
        language_filter = "en"
        title_suffix = " (English)"
    elif choice == "3":
        language_filter = "pt"
        title_suffix = " (Portuguese)"
    elif choice == "4":
        language_filter = "ja"
        title_suffix = " (Japanese)"
    elif choice == "5":
        limit = 1000
        title_suffix = " (Recent 1000 Posts)"
    
    # Get number of top words to show
    top_n = input("Number of top words to show (default=30): ").strip()
    top_n = int(top_n) if top_n.isdigit() else 30
    
    print(f"\n🔍 Fetching posts from database...")
    posts = get_posts_data(language_filter, limit)
    
    if not posts:
        print("❌ No posts found!")
        return
    
    print(f"✅ Fetched {len(posts)} posts")
    
    print(f"🔤 Analyzing word frequency...")
    word_freq = generate_word_frequency(posts, top_n)
    
    if not word_freq:
        print("❌ No words found after filtering!")
        return
    
    # Print statistics
    print_stats(posts, word_freq)
    
    # Create and show chart
    title = f"Bluesky Word Frequency{title_suffix}"
    create_frequency_chart(word_freq, title)
    
    print(f"\n✅ Analysis complete!")


if __name__ == "__main__":
    main()
