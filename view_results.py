#!/usr/bin/env python3
"""
View classification results from database
"""

import psycopg2
from config.config import DB_CONFIG

def view_results():
    """Display classification results"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("\n" + "="*120)
    print("📊 CLASSIFICATION RESULTS")
    print("="*120 + "\n")
    
    cur.execute("""
        SELECT 
            idea_id, 
            idea_title, 
            primary_theme, 
            secondary_themes,
            industry_name,
            theme_confidence,
            content_type
        FROM hackathon_ideas 
        WHERE classification_status = 'completed'
        ORDER BY idea_id
    """)
    
    results = cur.fetchall()
    
    if not results:
        print("No classified ideas found.")
        return
    
    for idx, row in enumerate(results, 1):
        idea_id, title, primary, secondary, industry, confidence, content_type = row
        
        print(f"🎯 Idea {idx}: {title}")
        print(f"   Primary Theme: {primary}")
        print(f"   Secondary Themes: {secondary}")
        print(f"   Industry: {industry}")
        print(f"   Confidence: {confidence:.2f}")
        print(f"   Content Type: {content_type}")
        print()
    
    print("="*120)
    print(f"✅ Total classified ideas: {len(results)}")
    print("="*120 + "\n")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    view_results()
