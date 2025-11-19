"""
Create rubrics table with dynamic rubric columns and weights
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.config import DB_CONFIG
import psycopg2


def create_rubrics_table():
    """Create evaluation_rubrics table with flexible rubric columns"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Create table with JSONB for dynamic rubrics
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_rubrics (
                rubric_id SERIAL PRIMARY KEY,
                rubric_set_name VARCHAR(100) UNIQUE NOT NULL,
                version VARCHAR(20) NOT NULL,
                
                -- Dynamic rubrics stored as JSON: {"novelty": 0.30, "clarity": 0.34, "feasibility": 0.15, ...}
                rubrics JSONB NOT NULL,
                
                -- Prompts
                system_prompt TEXT NOT NULL,
                user_prompt_template TEXT NOT NULL,
                scoring_guidelines TEXT,
                
                -- Metadata
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_rubric_active ON evaluation_rubrics(is_active);
            CREATE INDEX IF NOT EXISTS idx_rubrics_json ON evaluation_rubrics USING GIN (rubrics);
        """)
        
        conn.commit()
        print("✅ Rubrics table created successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    
    finally:
        cursor.close()
        conn.close()


def insert_sample_rubric():
    """Insert sample rubric with custom weights"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    system_prompt = (
        "You are a senior TCS technology evaluator with 15+ years experience. "
        "Conduct rigorous assessment using the provided rubric and weights. "
        "Output ONLY valid JSON matching the schema. Use exact weights provided."
    )
    
    user_prompt_template = (
        "EVALUATION CRITERIA WITH WEIGHTS:\n"
        "{rubric_criteria}\n\n"
        "IDEA TO EVALUATE:\n"
        "Title: {idea_title}\n"
        "Summary: {brief_summary}\n"
        "Challenge: {challenge_opportunity}\n"
        "Innovation: {novelty_benefits_risks}\n"
        "Theme: {primary_theme}\n"
        "Industry: {industry_name}\n"
        "Technologies: {technologies_extracted}\n"
        "Extracted Content: {extracted_files_content}\n\n"
        "REQUIRED OUTPUT FORMAT - Return valid JSON with this EXACT structure:\n"
        "{{\n"
        '  "scores": {{\n'
        '    "feasibility": {{"score": 7, "justification": "Brief explanation 2-3 sentences", "insufficient_info": false}},\n'
        '    "novelty": {{"score": 8, "justification": "Brief explanation", "insufficient_info": false}},\n'
        '    "clarity": {{"score": 6, "justification": "Brief explanation", "insufficient_info": false}}\n'
        '    ... include ALL rubric criteria from above ...\n'
        '  }},\n'
        '  "weighted_total": 7.2,\n'
        '  "investment_recommendation": "go",\n'
        '  "key_strengths": ["strength 1", "strength 2"],\n'
        '  "key_concerns": ["concern 1", "concern 2"]\n'
        "}}\n\n"
        "CRITICAL: Calculate weighted_total using the exact formula shown above. "
        "Score each criterion 1-10, then apply the weights."
    )

    
    scoring_guidelines = "Score 1-10: 9-10 Outstanding | 7-8 Strong | 5-6 Fair | 3-4 Weak | 1-2 Poor"
    
    # Sample rubrics with custom weights
    rubrics = {
        "feasibility": 0.15,
        "novelty": 0.30,
        "clarity": 0.34,
        "long_term_value": 0.10,
        "security_compliance": 0.08,
        "evidence": 0.03
    }
    
    try:
        import json
        
        cursor.execute("""
            INSERT INTO evaluation_rubrics (
                rubric_set_name, version, rubrics,
                system_prompt, user_prompt_template, scoring_guidelines,
                is_active
            ) VALUES (
                'custom-weights-example', 'v1.0', %s,
                %s, %s, %s, true
            )
            ON CONFLICT (rubric_set_name) DO UPDATE SET
                rubrics = EXCLUDED.rubrics,
                updated_at = CURRENT_TIMESTAMP
        """, (json.dumps(rubrics), system_prompt, user_prompt_template, scoring_guidelines))
        
        conn.commit()
        print("✅ Sample rubric inserted successfully!")
        print(f"   Rubrics: {rubrics}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}")
        raise
    
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    create_rubrics_table()
    insert_sample_rubric()
