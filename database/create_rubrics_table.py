"""
Create and populate evaluation rubrics table
"""

import psycopg2
from config.config import DB_CONFIG


def create_rubrics_table():
    """Create evaluation_rubrics table"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluation_rubrics (
                rubric_id SERIAL PRIMARY KEY,
                rubric_name VARCHAR(100) UNIQUE NOT NULL,
                version VARCHAR(20) NOT NULL,
                
                -- Criteria weights
                novelty_weight FLOAT NOT NULL,
                clarity_weight FLOAT NOT NULL,
                feasibility_weight FLOAT NOT NULL,
                long_term_value_weight FLOAT NOT NULL,
                security_compliance_weight FLOAT NOT NULL,
                evidence_weight FLOAT NOT NULL,
                
                -- Prompts
                system_prompt TEXT NOT NULL,
                user_prompt_template TEXT NOT NULL,
                scoring_guidelines TEXT NOT NULL,
                
                -- Metadata
                is_active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_rubric_active ON evaluation_rubrics(is_active);
        """)
        
        conn.commit()
        print("✓ Rubrics table created successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Failed to create rubrics table: {e}")
        raise
    
    finally:
        cursor.close()
        conn.close()


def insert_default_rubric():
    """Insert TCS default evaluation rubric"""
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    system_prompt = """You are a senior TCS technology evaluator with 15+ years assessing enterprise solutions and startup ideas. You understand TCS delivery models, enterprise security/compliance, and modernization roadmaps. Conduct a rigorous, SME-level assessment using the provided rubric.

Conduct rules:
- Use ONLY the information in the idea and supporting materials; do not invent facts.
- If information is missing for a criterion, set insufficient_info=true and score conservatively.
- Provide concise, evidence-based justifications (2–4 sentences each). Do NOT reveal chain-of-thought.
- Follow the weights exactly and compute weighted_total deterministically (formula provided).
- Output JSON only, strictly matching the schema; no extra keys, markdown, or commentary.
- Think harder: challenge assumptions, compare to alternatives, and avoid optimistic guessing."""

    user_prompt_template = """EXPERT EVALUATION CRITERIA & QUESTIONS (weights in parentheses):
1) NOVELTY (15%)
   - Problem significance; differentiation vs alternatives; market gap; category creation/disruption.
2) CLARITY (20%)
   - What/how/for whom; personas & buyers; value prop; differentiators; domain understanding.
3) FEASIBILITY (20%)
   - Technical approach credibility; integration complexity; resources & timeline; risks & mitigations; regulatory constraints.
4) LONG_TERM_VALUE (20%)
   - Business model; GTM; scalability; defensibility/switching costs; TAM expansion; enterprise trend alignment.
5) SECURITY_COMPLIANCE (15%)
   - Data handling (PII/PHI); authN/authZ; encryption (in transit/at rest); key mgmt; audit logging; AI misuse safeguards; regulatory mapping (GDPR, HIPAA, PCI DSS, ISO 27001, SOC 2).
6) EVIDENCE (10%)
   - PoC/demo; benchmarks/metrics; user feedback; references; professional completeness.

SCORING SCALE ANCHORS (1–10): 9–10 Outstanding | 7–8 Strong | 5–6 Fair | 3–4 Weak | 1–2 Poor

IDEA TO EVALUATE
Title: {idea_title}
Summary: {brief_summary}
Challenge: {challenge_opportunity}
Innovation: {novelty_benefits_risks}
Responsible AI: {responsible_ai}
Theme: {primary_theme}
Industry: {industry_name}
Technologies: {technologies_extracted}
Extracted Content: {extracted_files_content}

RESPONSE FORMAT & RULES
Return ONLY a JSON object with this structure:
{{
  "novelty": {{"score": 1-10, "justification": "string", "insufficient_info": false}},
  "clarity": {{"score": 1-10, "justification": "string", "insufficient_info": false}},
  "feasibility": {{"score": 1-10, "justification": "string", "insufficient_info": false}},
  "long_term_value": {{"score": 1-10, "justification": "string", "insufficient_info": false}},
  "security_compliance": {{"score": 1-10, "justification": "string", "insufficient_info": false}},
  "evidence": {{"score": 1-10, "justification": "string", "insufficient_info": false}},
  "weighted_total": 0.0,
  "investment_recommendation": "go|consider-with-mitigations|no-go",
  "key_strengths": ["strength1", "strength2"],
  "key_concerns": ["concern1", "concern2"],
  "assumptions": ["assumption1"],
  "flags": ["flag1"]
}}

Compute weighted_total: WT = 0.15*n + 0.20*c + 0.20*f + 0.20*l + 0.15*s + 0.10*e"""

    scoring_guidelines = """SCORING GUIDELINES (per criterion, 1–10):

Novelty / Market Need:
  9–10: World-first or category-creating with clear client impact.
  7–8: Industry-first in sector/region or step-change over status quo.
  5–6: TCS-first or materially ahead of current TCS/partner offerings.
  4: Unit/BG-first; mostly incremental within a BU/context.
  1–3: Derivative; no meaningful gap identified.

Solution Clarity & Targeting:
  9/10: Clearly articulated; unambiguous scope & personas; strong narrative.
  7/8: Clear but can be refined (minor ambiguities).
  5/6: Satisfactory; key elements present but uneven.
  3/4: Unclear/contradictory; material gaps.
  1/2: Incoherent or missing fundamentals.

Implementation Feasibility:
  9–10: Architecture, data flows, dependencies explicit; risks mitigated; realistic resourcing/timeline.
  7–8: Solid plan with minor gaps; risks manageable.
  5–6: Plausible but significant unknowns or missing milestones/owners.
  3–4: High technical/integration risk; weak resourcing.
  1–2: Unrealistic with current tech/constraints.

Long-Term Value & Sustenance:
  9–10: Strong economics & defensibility (IP/data/network); clear GTM; scalable; trend-aligned.
  7–8: Good path to scale with a few open questions.
  5–6: Some value but uncertain durability/expansion path.
  3–4: Narrow/one-off; limited reuse; weak economics.
  1–2: Low or negative long-term value.

Security & Compliance:
  9–10: Privacy-by-design; concrete controls (IAM, least privilege, KMS, logging, DLP); regs mapped; AI misuse safeguards.
  7–8: Most controls addressed with minor gaps.
  5–6: Partial coverage; risks noted but not mitigated.
  3–4: Material gaps (residency/retention/access).
  1–2: Non-compliant or high-risk by design.

Evidence & Documentation:
  9–10: Compelling evidence (prototype) and thorough docs.
  7–8: Wireframes/mockups with solid documentation.
  5–6: Light evidence (more documentation needed).
  1–4: Poor documentation or no evidence."""

    try:
        cursor.execute("""
            INSERT INTO evaluation_rubrics (
                rubric_name, version,
                novelty_weight, clarity_weight, feasibility_weight,
                long_term_value_weight, security_compliance_weight, evidence_weight,
                system_prompt, user_prompt_template, scoring_guidelines,
                is_active
            ) VALUES (
                'tcs-ideathon-v2', 'v2.0',
                0.15, 0.20, 0.20, 0.20, 0.15, 0.10,
                %s, %s, %s, true
            )
            ON CONFLICT (rubric_name) DO UPDATE SET
                updated_at = CURRENT_TIMESTAMP
        """, (system_prompt, user_prompt_template, scoring_guidelines))
        
        conn.commit()
        print("✓ Default rubric inserted successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Failed to insert rubric: {e}")
        raise
    
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    create_rubrics_table()
    insert_default_rubric()
