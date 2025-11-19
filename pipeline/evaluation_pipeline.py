"""
Evaluation Pipeline - Uses dynamic rubrics from table
"""

import logging
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import json

from evaluation.idea_evaluator import IdeaEvaluator
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class EvaluationPipeline:
    """Pipeline for evaluating ideas using dynamic rubrics"""
    
    def __init__(
        self,
        evaluator: IdeaEvaluator,
        db_manager: DatabaseManager,
        max_workers: int = 8
    ):
        self.evaluator = evaluator
        self.db_manager = db_manager
        self.max_workers = max_workers
        self.rubric_config = None
    
    def evaluate_all_ideas(self) -> Dict[str, int]:
        """Evaluate all ideas using active rubric"""
        
        # Load active rubric configuration
        self.rubric_config = self._load_active_rubric()
        
        if not self.rubric_config:
            print("\n⚠️  No active rubric found in database")
            print("   To create rubrics table, run: python database/setup_rubrics.py")
            return {'total': 0, 'completed': 0, 'failed': 0}
        
        # Parse rubrics JSON
        rubrics_data = self.rubric_config.get('rubrics')
        if isinstance(rubrics_data, str):
            rubrics = json.loads(rubrics_data)
        else:
            rubrics = rubrics_data
        
        # Display rubrics being used
        print(f"\n{'='*80}")
        print(f"📊 ACTIVE RUBRICS: {self.rubric_config['rubric_set_name']} ({self.rubric_config['version']})")
        print(f"{'='*80}")
        for criterion, weight in rubrics.items():
            print(f"   {criterion.replace('_', ' ').title()}: {weight:.2%}")
        print(f"{'='*80}\n")
        
        # Fetch ideas
        ideas = self._fetch_unevaluated_ideas()
        
        if not ideas:
            print("✓ No ideas need evaluation")
            return {'total': 0, 'completed': 0, 'failed': 0}
        
        print(f"🎯 Processing {len(ideas)} ideas with {self.max_workers} workers\n")
        
        stats = {'total': len(ideas), 'completed': 0, 'failed': 0}
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idea = {
                executor.submit(self._evaluate_single_idea, idea, rubrics): idea
                for idea in ideas
            }
            
            with tqdm(total=len(ideas), desc="Evaluating ideas") as pbar:
                for future in as_completed(future_to_idea):
                    try:
                        future.result()
                        stats['completed'] += 1
                    except Exception as e:
                        logger.error(f"Evaluation failed: {e}")
                        stats['failed'] += 1
                    pbar.update(1)
        
        return stats
    
    def _load_active_rubric(self) -> Dict:
        """Load active rubric from database"""
        cursor = self.db_manager.connection.cursor()
        
        try:
            # Check if table exists first
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'evaluation_rubrics'
                )
            """)
            
            table_exists = cursor.fetchone()[0]
            
            if not table_exists:
                return None
            
            # Fetch active rubric
            cursor.execute("""
                SELECT 
                    rubric_id, rubric_set_name, version, rubrics,
                    system_prompt, user_prompt_template, scoring_guidelines,
                    is_active, created_at, updated_at
                FROM evaluation_rubrics
                WHERE is_active = true
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            
            if not row:
                return None
            
            # Manually map columns (avoid descriptor issues)
            return {
                'rubric_id': row[0],
                'rubric_set_name': row[1],
                'version': row[2],
                'rubrics': row[3],
                'system_prompt': row[4],
                'user_prompt_template': row[5],
                'scoring_guidelines': row[6],
                'is_active': row[7],
                'created_at': row[8],
                'updated_at': row[9]
            }
            
        except Exception as e:
            logger.error(f"Failed to load rubric: {e}")
            return None
            
        finally:
            cursor.close()
    
    def _fetch_unevaluated_ideas(self) -> List[Dict]:
        """Fetch ideas that need evaluation"""
        cursor = self.db_manager.connection.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    idea_id, idea_title, brief_summary, challenge_opportunity,
                    novelty_benefits_risks, responsible_ai, extracted_files_content,
                    primary_theme, industry_name, technologies_extracted
                FROM hackathon_ideas
                WHERE classification_status = 'completed'
                  AND (evaluation_status IS NULL OR evaluation_status = 'pending')
            """)
            
            rows = cursor.fetchall()
            
            # Manually map columns
            ideas = []
            for row in rows:
                ideas.append({
                    'idea_id': row[0],
                    'idea_title': row[1],
                    'brief_summary': row[2],
                    'challenge_opportunity': row[3],
                    'novelty_benefits_risks': row[4],
                    'responsible_ai': row[5],
                    'extracted_files_content': row[6],
                    'primary_theme': row[7],
                    'industry_name': row[8],
                    'technologies_extracted': row[9]
                })
            
            return ideas
            
        finally:
            cursor.close()
    
    def _evaluate_single_idea(self, idea: Dict, rubrics: Dict[str, float]):
        """Evaluate a single idea"""
        idea_id = idea['idea_id']
        
        print(f"\n📊 Evaluating idea {idea_id}")
        
        try:
            result = self.evaluator.evaluate_idea(
                idea_data=idea,
                system_prompt=self.rubric_config['system_prompt'],
                user_prompt_template=self.rubric_config['user_prompt_template'],
                rubrics=rubrics
            )
            
            self._update_evaluation(idea_id, result)
            print(f"  ✓ Score: {result['weighted_total']:.2f}/10 - {result['investment_recommendation']}")
            
        except Exception as e:
            logger.error(f"Evaluation failed for {idea_id}: {e}")
            self._mark_failed(idea_id, str(e))
            raise
    
    def _update_evaluation(self, idea_id: str, result: Dict):
        """Update database with evaluation results"""
        cursor = self.db_manager.connection.cursor()
        
        try:
            cursor.execute("""
                UPDATE hackathon_ideas
                SET 
                    evaluation_scores = %s,
                    weighted_total_score = %s,
                    investment_recommendation = %s,
                    key_strengths = %s,
                    key_concerns = %s,
                    evaluation_status = 'completed',
                    updated_at = CURRENT_TIMESTAMP
                WHERE idea_id = %s
            """, (
                json.dumps(result.get('scores', {})),
                result['weighted_total'],
                result.get('investment_recommendation', 'consider-with-mitigations'),
                json.dumps(result.get('key_strengths', [])),
                json.dumps(result.get('key_concerns', [])),
                idea_id
            ))
            
            self.db_manager.connection.commit()
            
        finally:
            cursor.close()
    
    def _mark_failed(self, idea_id: str, error: str):
        """Mark evaluation as failed"""
        cursor = self.db_manager.connection.cursor()
        
        try:
            cursor.execute("""
                UPDATE hackathon_ideas
                SET 
                    evaluation_status = 'failed',
                    error_message = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE idea_id = %s
            """, (error, idea_id))
            
            self.db_manager.connection.commit()
            
        finally:
            cursor.close()
