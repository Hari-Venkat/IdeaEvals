"""
Classification Pipeline - Runs after extraction
Classifies themes, industries, and technologies
"""

import logging
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import json

from classification.tcs_classifier import TCSClassifier
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ClassificationPipeline:
    """Pipeline for classifying extracted ideas"""
    
    def __init__(
        self,
        classifier: TCSClassifier,
        db_manager: DatabaseManager,
        max_workers: int = 5
    ):
        self.classifier = classifier
        self.db_manager = db_manager
        self.max_workers = max_workers
    
    def classify_all_ideas(self) -> Dict[str, int]:
        """Classify all ideas that have been extracted but not classified"""
        
        # Fetch ideas that need classification
        ideas = self._fetch_unclassified_ideas()
        
        if not ideas:
            print("✓ No ideas need classification")
            return {'total': 0, 'completed': 0, 'failed': 0}
        
        print(f"\n{'='*80}")
        print(f"🎯 STARTING CLASSIFICATION - Processing {len(ideas)} ideas")
        print(f"{'='*80}\n")
        
        stats = {
            'total': len(ideas),
            'completed': 0,
            'failed': 0
        }
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idea = {
                executor.submit(self._classify_single_idea, idea): idea
                for idea in ideas
            }
            
            with tqdm(total=len(ideas), desc="Classifying ideas") as pbar:
                for future in as_completed(future_to_idea):
                    idea = future_to_idea[future]
                    try:
                        future.result()
                        stats['completed'] += 1
                    except Exception as e:
                        logger.error(f"Failed to classify idea {idea['idea_id']}: {e}")
                        stats['failed'] += 1
                    
                    pbar.update(1)
        
        return stats
    
    def _fetch_unclassified_ideas(self) -> List[Dict]:
        """Fetch ideas from DB that need classification"""
        cursor = self.db_manager.connection.cursor()
        
        try:
            cursor.execute("""
                SELECT 
                    idea_id,
                    idea_title,
                    brief_summary,
                    challenge_opportunity,
                    novelty_benefits_risks,
                    responsible_ai,
                    extracted_files_content
                FROM hackathon_ideas
                WHERE extraction_status = 'completed'
                  AND (classification_status IS NULL OR classification_status = 'pending')
            """)
            
            # ✅ FIX: Extract column names correctly
            column_names = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            # ✅ FIX: Convert to list of dicts properly
            return [dict(zip(column_names, row)) for row in rows]
            
        finally:
            cursor.close()
    
    def _classify_single_idea(self, idea: Dict):
        """Classify a single idea"""
        
        idea_id = idea['idea_id']
        
        print(f"\n🔍 Classifying idea {idea_id}")
        
        try:
            # Combine all text for classification
            combined_text = self._combine_idea_text(idea)
            
            # Run classification
            results = self.classifier.classify_all(combined_text)
            
            # Extract results
            theme = results['theme']
            industry = results['industry']
            tech = results['technologies']
            
            # Update database
            self._update_classification(
                idea_id=idea_id,
                theme=theme,
                industry=industry,
                tech=tech
            )
            
            print(f"  ✓ Theme: {theme['primary_theme']}")
            print(f"  ✓ Industry: {industry['industry_name']}")
            print(f"  ✓ Technologies: {', '.join(tech['technologies_extracted'][:3])}")
            
        except Exception as e:
            logger.error(f"Classification failed for {idea_id}: {e}")
            self._mark_classification_failed(idea_id, str(e))
            raise
    
    def _combine_idea_text(self, idea: Dict) -> str:
        """Combine all relevant text fields for classification"""
        parts = []
        
        if idea.get('idea_title'):
            parts.append(f"Title: {idea['idea_title']}")
        
        if idea.get('brief_summary'):
            parts.append(f"Summary: {idea['brief_summary']}")
        
        if idea.get('challenge_opportunity'):
            parts.append(f"Challenge: {idea['challenge_opportunity']}")
        
        if idea.get('novelty_benefits_risks'):
            parts.append(f"Innovation: {idea['novelty_benefits_risks']}")
        
        if idea.get('responsible_ai'):
            parts.append(f"Responsible AI: {idea['responsible_ai']}")
        
        if idea.get('extracted_files_content'):
            # Truncate to avoid token limits (keep first 5000 chars)
            content = idea['extracted_files_content'][:5000]
            parts.append(f"Extracted Content: {content}")
        
        return "\n\n".join(parts)
    
    def _update_classification(
        self,
        idea_id: str,
        theme: Dict,
        industry: Dict,
        tech: Dict
    ):
        """Update database with classification results"""
        
        cursor = self.db_manager.connection.cursor()
        
        try:
            cursor.execute("""
                UPDATE hackathon_ideas
                SET 
                    primary_theme = %s,
                    secondary_themes = %s,
                    theme_confidence = %s,
                    theme_rationale = %s,
                    industry_name = %s,
                    industry_confidence = %s,
                    industry_rationale = %s,
                    technologies_extracted = %s,
                    technology_rationale = %s,
                    classification_status = 'completed',
                    updated_at = CURRENT_TIMESTAMP
                WHERE idea_id = %s
            """, (
                theme['primary_theme'],
                json.dumps(theme['secondary_themes']),
                theme['confidence'],
                theme['rationale'],
                industry['industry_name'],
                industry['confidence'],
                industry['rationale'],
                json.dumps(tech['technologies_extracted']),
                tech['rationale'],
                idea_id
            ))
            
            self.db_manager.connection.commit()
            
        finally:
            cursor.close()
    
    def _mark_classification_failed(self, idea_id: str, error: str):
        """Mark classification as failed"""
        cursor = self.db_manager.connection.cursor()
        
        try:
            cursor.execute("""
                UPDATE hackathon_ideas
                SET 
                    classification_status = 'failed',
                    error_message = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE idea_id = %s
            """, (error, idea_id))
            
            self.db_manager.connection.commit()
            
        finally:
            cursor.close()
