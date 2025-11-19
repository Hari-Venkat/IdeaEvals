#!/usr/bin/env python3
"""
View detailed technology extraction results
"""

import psycopg2
import json
from config.config import DB_CONFIG

def view_technologies():
    """Display detailed technology extraction"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    print("\n" + "="*120)
    print("💻 DETAILED TECHNOLOGY EXTRACTION RESULTS")
    print("="*120 + "\n")
    
    cur.execute("""
        SELECT 
            idea_id,
            idea_title,
            primary_theme,
            industry_name,
            technologies_extracted,
            technology_rationale
        FROM hackathon_ideas 
        WHERE classification_status = 'completed'
        ORDER BY idea_id
    """)
    
    results = cur.fetchall()
    
    if not results:
        print("No classified ideas found.")
        return
    
    for idx, row in enumerate(results, 1):
        idea_id, title, theme, industry, tech_json, rationale = row
        
        # Parse technologies JSON
        try:
            technologies = json.loads(tech_json) if tech_json else []
        except:
            technologies = []
        
        print(f"{'='*120}")
        print(f"Idea {idx}: {title}")
        print(f"{'='*120}")
        print(f"🎯 Theme: {theme}")
        print(f"🏢 Industry: {industry}")
        print(f"\n💻 Technologies Extracted ({len(technologies)}):")
        
        if technologies:
            for i, tech in enumerate(technologies, 1):
                print(f"   {i:2d}. {tech}")
        else:
            print("   (No technologies extracted)")
        
        print(f"\n📝 Extraction Rationale:")
        if rationale:
            # Wrap text at 100 characters
            words = rationale.split()
            line = "   "
            for word in words:
                if len(line) + len(word) + 1 > 100:
                    print(line)
                    line = "   " + word
                else:
                    line += " " + word if line != "   " else word
            if line.strip():
                print(line)
        else:
            print("   (No rationale provided)")
        
        print()
    
    print("="*120)
    
    # Summary statistics
    cur.execute("""
        SELECT 
            AVG(json_array_length(technologies_extracted::json)) as avg_tech_count,
            MIN(json_array_length(technologies_extracted::json)) as min_tech_count,
            MAX(json_array_length(technologies_extracted::json)) as max_tech_count
        FROM hackathon_ideas 
        WHERE classification_status = 'completed'
          AND technologies_extracted IS NOT NULL
    """)
    
    stats = cur.fetchone()
    if stats and stats[0]:
        print(f"\n📊 Technology Extraction Statistics:")
        print(f"   Average technologies per idea: {stats[0]:.1f}")
        print(f"   Minimum: {stats[1]}")
        print(f"   Maximum: {stats[2]}")
    
    print("\n" + "="*120 + "\n")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    view_technologies()
