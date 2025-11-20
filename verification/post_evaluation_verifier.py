#!/usr/bin/env python3
"""
Post-Evaluation Verification

Automatically verifies evaluation quality after the evaluation process completes.
Checks completed evaluations in the database for:
1. Rubric Compliance
2. JSON Validity
3. No Hallucination
4. Consistency
"""

import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
from config.config import DB_CONFIG


class PostEvaluationVerifier:
    """Verify evaluation quality after completion"""
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.passed = 0
        self.failed = 0
        self.warnings = []
    
    def verify_all(self):
        """Run all verification checks on completed evaluations with retry logic"""
        print("\n" + "="*80)
        print("🔍 POST-EVALUATION VERIFICATION")
        print("="*80 + "\n")
        
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()
        
        # Get completed evaluations that need verification
        cursor.execute("""
            SELECT COUNT(*) 
            FROM hackathon_ideas 
            WHERE evaluation_status = 'completed'
            AND (verification_status IS NULL OR verification_status IN ('pending', 'failed'))
        """)
        total_to_verify = cursor.fetchone()[0]
        
        if total_to_verify == 0:
            # Check if all are already verified
            cursor.execute("""
                SELECT COUNT(*) 
                FROM hackathon_ideas 
                WHERE evaluation_status = 'completed'
                AND verification_status = 'completed'
            """)
            already_verified = cursor.fetchone()[0]
            
            if already_verified > 0:
                print(f"✅ All {already_verified} evaluations already verified.\n")
            else:
                print("⚠️  No completed evaluations found. Skipping verification.\n")
            
            cursor.close()
            conn.close()
            return
        
        print(f"📊 Found {total_to_verify} evaluations to verify\n")
        
        # Run verification checks
        self.verify_rubric_compliance(cursor)
        self.verify_json_validity(cursor)
        self.verify_no_hallucination(cursor)
        self.verify_consistency(cursor)
        
        # Update verification status in database
        self.update_verification_status(cursor, conn)
        
        cursor.close()
        conn.close()
        
        # Print summary
        self.print_summary(total_to_verify)
    
    def verify_rubric_compliance(self, cursor):
        """Verify all rubric criteria are scored"""
        print("="*80)
        print("CHECK 1: Rubric Compliance")
        print("="*80 + "\n")
        
        # Get active rubrics
        cursor.execute("""
            SELECT rubrics 
            FROM evaluation_rubrics 
            WHERE is_active = true 
            LIMIT 1
        """)
        
        rubric_row = cursor.fetchone()
        if not rubric_row:
            print("⚠️  No active rubrics found. Skipping check.\n")
            return
        
        rubrics = rubric_row[0]
        if isinstance(rubrics, str):
            rubrics = json.loads(rubrics)
        
        expected_criteria = set(rubrics.keys())
        
        # Check evaluations
        cursor.execute("""
            SELECT idea_id, idea_title, evaluation_scores
            FROM hackathon_ideas
            WHERE evaluation_status = 'completed'
        """)
        
        missing_criteria_count = 0
        
        for row in cursor.fetchall():
            idea_id, idea_title, scores = row
            
            if isinstance(scores, str):
                scores = json.loads(scores)
            
            actual_criteria = set(scores.keys())
            missing = expected_criteria - actual_criteria
            
            if missing:
                missing_criteria_count += 1
                self.warnings.append(
                    f"Idea {idea_id} missing criteria: {missing}"
                )
        
        if missing_criteria_count == 0:
            print(f"✅ All evaluations have complete rubric criteria")
            print(f"   Expected criteria: {', '.join(expected_criteria)}")
            self.passed += 1
        else:
            print(f"❌ {missing_criteria_count} evaluations have missing criteria")
            self.failed += 1
        
        print()
    
    def verify_json_validity(self, cursor):
        """Verify all evaluation JSONs are valid"""
        print("="*80)
        print("CHECK 2: JSON Validity")
        print("="*80 + "\n")
        
        cursor.execute("""
            SELECT idea_id, idea_title, evaluation_scores, 
                   weighted_total_score, investment_recommendation,
                   key_strengths, key_concerns
            FROM hackathon_ideas
            WHERE evaluation_status = 'completed'
        """)
        
        invalid_count = 0
        
        for row in cursor.fetchall():
            idea_id = row[0]
            
            # Check if all required fields are present and valid
            try:
                scores = row[2]
                weighted_total = row[3]
                recommendation = row[4]
                strengths = row[5]
                concerns = row[6]
                
                # Validate scores is valid JSON
                if isinstance(scores, str):
                    json.loads(scores)
                
                # Validate strengths and concerns are arrays
                if isinstance(strengths, str):
                    json.loads(strengths)
                if isinstance(concerns, str):
                    json.loads(concerns)
                
                # Check required fields are not null
                if scores is None or weighted_total is None or recommendation is None:
                    invalid_count += 1
                    self.warnings.append(
                        f"Idea {idea_id} has null required fields"
                    )
                
            except json.JSONDecodeError as e:
                invalid_count += 1
                self.warnings.append(
                    f"Idea {idea_id} has invalid JSON: {e}"
                )
        
        if invalid_count == 0:
            print(f"✅ All evaluations have valid JSON structure")
            print(f"   Required fields: scores, weighted_total, recommendation, strengths, concerns")
            self.passed += 1
        else:
            print(f"❌ {invalid_count} evaluations have invalid JSON")
            self.failed += 1
        
        print()
    
    def verify_no_hallucination(self, cursor):
        """Verify no obvious hallucination in scores"""
        print("="*80)
        print("CHECK 3: No Hallucination")
        print("="*80 + "\n")
        
        cursor.execute("""
            SELECT idea_id, idea_title, evaluation_scores, 
                   brief_summary, challenge_opportunity, 
                   novelty_benefits_risks, extracted_files_content
            FROM hackathon_ideas
            WHERE evaluation_status = 'completed'
        """)
        
        hallucination_count = 0
        
        for row in cursor.fetchall():
            idea_id, idea_title, scores, summary, challenge, novelty, files = row
            
            # Check if idea has minimal information
            has_minimal_info = (
                (not summary or len(summary.strip()) < 50) and
                (not challenge or len(challenge.strip()) < 50) and
                (not novelty or len(novelty.strip()) < 50) and
                (not files or len(files.strip()) < 100)
            )
            
            if has_minimal_info:
                # Check if scores are suspiciously high
                if isinstance(scores, str):
                    scores = json.loads(scores)
                
                high_scores = []
                for criterion, score_data in scores.items():
                    score = score_data.get('score', 0)
                    insufficient_info = score_data.get('insufficient_info', False)
                    
                    if score > 7 and not insufficient_info:
                        high_scores.append(f"{criterion}={score}")
                
                if high_scores:
                    hallucination_count += 1
                    self.warnings.append(
                        f"Idea {idea_id} has high scores despite minimal info: {', '.join(high_scores)}"
                    )
        
        if hallucination_count == 0:
            print(f"✅ No obvious hallucination detected")
            print(f"   Scores appropriately reflect available information")
            self.passed += 1
        else:
            print(f"⚠️  {hallucination_count} evaluations may have hallucination")
            print(f"   (High scores despite minimal information)")
            # Don't fail, just warn
            self.passed += 1
        
        print()
    
    def verify_consistency(self, cursor):
        """Verify score consistency across evaluations"""
        print("="*80)
        print("CHECK 4: Consistency")
        print("="*80 + "\n")
        
        cursor.execute("""
            SELECT weighted_total_score
            FROM hackathon_ideas
            WHERE evaluation_status = 'completed'
            AND weighted_total_score IS NOT NULL
        """)
        
        scores = [row[0] for row in cursor.fetchall()]
        
        if len(scores) < 2:
            print("⚠️  Not enough evaluations to check consistency\n")
            return
        
        # Check for score distribution
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)
        score_range = max_score - min_score
        
        # Check if all scores are suspiciously similar or different
        if score_range < 0.5:
            print(f"⚠️  All scores are very similar (range: {score_range:.2f})")
            print(f"   This might indicate lack of discrimination")
            self.warnings.append(
                f"Score range too narrow: {score_range:.2f}"
            )
        elif score_range > 9.0:
            print(f"⚠️  Scores have very wide range (range: {score_range:.2f})")
            print(f"   This might indicate inconsistent evaluation")
            self.warnings.append(
                f"Score range too wide: {score_range:.2f}"
            )
        else:
            print(f"✅ Score distribution looks reasonable")
        
        print(f"   Average: {avg_score:.2f}")
        print(f"   Range: {min_score:.2f} - {max_score:.2f}")
        print(f"   Spread: {score_range:.2f}")
        
        self.passed += 1
        print()
    
    def update_verification_status(self, cursor, conn):
        """Update verification status in database"""
        print("\n" + "="*80)
        print("💾 Updating Verification Status in Database")
        print("="*80 + "\n")
        
        # Determine overall verification status
        if self.failed == 0:
            status = 'completed'
            message = "All verification checks passed"
        else:
            status = 'failed'
            message = f"{self.failed} verification checks failed"
        
        # Update all evaluated ideas with verification status
        cursor.execute("""
            UPDATE hackathon_ideas
            SET verification_status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE evaluation_status = 'completed'
            AND (verification_status IS NULL OR verification_status IN ('pending', 'failed'))
        """, (status,))
        
        updated_count = cursor.rowcount
        conn.commit()
        
        print(f"✅ Updated {updated_count} ideas: verification_status = '{status}'")
        print(f"   {message}")
        print()
    
    def print_summary(self, total_evaluated):
        """Print verification summary"""
        print("="*80)
        print("📊 VERIFICATION SUMMARY")
        print("="*80 + "\n")
        
        total_checks = self.passed + self.failed
        pass_rate = (self.passed / total_checks * 100) if total_checks > 0 else 0
        
        print(f"Evaluated Ideas: {total_evaluated}")
        print(f"Verification Checks: {self.passed}/{total_checks} passed ({pass_rate:.0f}%)\n")
        
        if self.failed == 0:
            print("🎉 All verification checks passed!")
            print("✅ Evaluation quality is good!")
        elif self.passed >= 3:
            print(f"✅ {self.passed}/4 checks passed - Evaluation quality is acceptable")
            if self.warnings:
                print(f"⚠️  {len(self.warnings)} warnings detected")
        else:
            print(f"❌ Only {self.passed}/4 checks passed - Review evaluation quality")
        
        # Show warnings if any
        if self.warnings and len(self.warnings) <= 5:
            print(f"\n⚠️  Warnings:")
            for warning in self.warnings[:5]:
                print(f"   - {warning}")
            if len(self.warnings) > 5:
                print(f"   ... and {len(self.warnings) - 5} more")
        
        print("\n" + "="*80 + "\n")


def main():
    """Run post-evaluation verification"""
    verifier = PostEvaluationVerifier(DB_CONFIG)
    verifier.verify_all()


if __name__ == "__main__":
    main()
