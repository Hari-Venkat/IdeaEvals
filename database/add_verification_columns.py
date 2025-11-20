#!/usr/bin/env python3
"""
Add verification_status column to existing database
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from config.config import DB_CONFIG


def add_verification_column():
    """Add verification_status column to hackathon_ideas table"""
    
    print("\n" + "="*80)
    print("Adding Verification Status Column to Database")
    print("="*80 + "\n")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Check if column already exists
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'hackathon_ideas' 
        AND column_name = 'verification_status'
    """)
    
    if cursor.fetchone():
        print("✅ verification_status column already exists")
        cursor.close()
        conn.close()
        return
    
    # Add column
    try:
        cursor.execute("""
            ALTER TABLE hackathon_ideas 
            ADD COLUMN verification_status VARCHAR(50) DEFAULT 'pending'
        """)
        conn.commit()
        print("✅ Added column: verification_status")
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        conn.rollback()
    
    cursor.close()
    conn.close()
    
    print("\n✅ Verification column added successfully!\n")


if __name__ == "__main__":
    add_verification_column()
