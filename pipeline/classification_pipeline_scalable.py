"""
Scalable Classification Pipeline for Large-Scale Processing (500K+ ideas)
Includes: Rate limiting, batch processing, retry logic, progress tracking
"""

import logging
import time
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import json

from classification.tcs_classifier import TCSClassifier
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class ScalableClassificationPipeline:
    """Scalable pipeline for classifying large volumes of ideas"""
    
    def __init__(
        self,
        classifier: TCSClassifier,
        db_manager: DatabaseManager,
        max_workers: int = 8,
        batch_size: int = 1000,
        rate_limit_rpm: int = 15,  # requests per minute
        max_retries: int = 3
    ):
        self.classifier = classifier
        self.db_manager = db_manager
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.rate_limit_rpm = rate_limit_rpm
        self.max_retries = max_retries
        
        # Rate limiting
        self.min_delay = 60.0 / rate_limit_rpm  # seconds between requests
        self.last_request_time = 0
    
    def classify_all_ideas(self) -> Dict[str, int]:
        """Classify all ideas with batch processing and rate limiting"""
        
        # Get total count first
        total_count = self._get_unclassified_count()
        
        if total_count == 0:
            print("✓ No ideas need classification")
            return {'total': 0, 'completed': 0, 'failed': 0}
        
        print(f"\n{'='*80}")
        print(f"🎯 STARTING SCALABLE CLASSIFICATION")
        print(f"   Total Ideas: {total_count:,}")
        print(f"   Batch Size: {self.batch_size:,}")
        print(f"   Workers: {self.max_workers}")
        print(f"   Rate Limit: {self.rate_limit_rpm} requests/minute")
        print(f"{'='*80}\n")
        
        stats = {
            'total': total_count,
            'completed': 0,
            'failed': 0,
            'batches_processed': 0
        }
        
        # Process in batches
        offset = 0
        with tqdm(total=total_count, desc="Overall Progress") as overall_pbar:
            while offset < total_count:
                batch_ideas = self._fetch_batch(offset, self.batch_size)
                
                if not batch_ideas:
                    break
                
                batch_stats = self._process_batch(batch_ideas)
                
                stats['completed'] += batch_stats['completed']
                stats['failed'] += batch_stats['failed']
                stats['batches_processed'] += 1
                
                overall_pbar.update(len(batch_ideas))
                
                # Log progress
                logger.info(
                    f"Batch {stats['batches_processed']}: "
                    f"{stats['completed']}/{stats['total']} completed, "
                    f"{stats['failed']} failed"
                )
                
                offset += self.batch_size
                
                # Commit after each batch
                self.db_manager.connection.commit()
        
        return stats
    
    def _get_unclassified_count(self) -> int:
        """Get count of unclassified ideas"""
        cursor = self.db_manager.connection.cursor()
        try:
            cursor.execute("""
                SELECT COUNT(*)
                FROM hackathon_ideas
                WHERE extraction_status = 'completed'
                  AND (classification_status IS NULL OR classification_status = 'pending')
            """)
            return cursor.fetchone()[0]
        finally:
            cursor.close()
    
    def _fetch_batch(self, offset: int, limit: int) -> List[Dict]:
        """Fetch a batch of ideas for processing"""
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
                ORDER BY idea_id
                LIMIT %s OFFSET %s
            """, (limit, offset))
            
            column_names = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(column_names, row)) for row in rows]
            
        finally:
            cursor.close()
    
    def _process_batch(self, ideas: List[Dict]) -> Dict[str, int]:
        """Process a batch of ideas with rate limiting"""
        
        stats = {'completed': 0, 'failed': 0}
        
        # Use ThreadPoolExecutor for parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_idea = {
                executor.submit(self._classify_with_retry, idea): idea
                for idea in ideas
            }
            
            for future in as_completed(future_to_idea):
                idea = future_to_idea[future]
                try:
                    future.result()
                    stats['completed'] += 1
                except Exception as e:
                    logger.error(f"Failed to classify idea {idea['idea_id']}: {e}")
                    stats['failed'] += 1
        
        return stats
    
    def _classify_with_retry(self, idea: Dict):
        """Classify a single idea with retry logic"""
        
        idea_id = idea['idea_id']
        
        for attempt in range(self.max_retries):
            try:
                # Rate limiting
                self._wait_for_rate_limit()
                
                # Combine all text for classification
                combined_text = self._combine_idea_text(idea)
                
                # Run classification (single API call)
                results = self.classifier.classify_all(combined_text)
                
                # Update database
                self._update_classification(
                    idea_id=idea_id,
                    theme=results['theme'],
                    industry=results['industry'],
                    tech=results['technologies']
                )
                
                return  # Success
                
            except Exception as e:
                error_msg = str(e)
                
                # Check if it's a rate limit error
                if '429' in error_msg or 'quota' in error_msg.lower():
                    wait_time = (attempt + 1) * 10  # Exponential backoff
                    logger.warning(
                        f"Rate limit hit for {idea_id}, "
                        f"waiting {wait_time}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                
                # Other errors
                if attempt == self.max_retries - 1:
                    # Final attempt failed
                    self._mark_classification_failed(idea_id, error_msg)
                    raise
                else:
                    logger.warning(
                        f"Classification failed for {idea_id}, "
                        f"retrying (attempt {attempt + 1}/{self.max_retries}): {error_msg}"
                    )
                    time.sleep(2 ** attempt)  # Exponential backoff
    
    def _wait_for_rate_limit(self):
        """Implement rate limiting between requests"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        
        if time_since_last < self.min_delay:
            sleep_time = self.min_delay - time_since_last
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
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
            # Truncate to avoid token limits
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
            
        finally:
            cursor.close()
