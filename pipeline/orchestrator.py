from pathlib import Path
from typing import Dict, List
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from extraction.file_extractor import FileExtractor
from extraction.content_processor import ContentProcessor

from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    def __init__(
        self,
        extractor: FileExtractor,
        db_manager: DatabaseManager,
        additional_files_dir: Path,
        max_workers: int = 5,
        max_file_workers: int = 3,
        api_key: str = None  # Not needed anymore
    ):
        self.extractor = extractor
        
        # ✅ No prototype detector needed - extractor does it all
        self.processor = ContentProcessor(extractor, max_file_workers=max_file_workers)
        
        self.db_manager = db_manager
        self.additional_files_dir = additional_files_dir
        self.max_workers = max_workers
    
    def process_all_ideas(self, ideas: List[Dict]) -> Dict[str, int]:
        """Process all ideas with parallel execution."""
        
        print(f"\n{'='*80}")
        print(f"🚀 STARTING PIPELINE - Processing {len(ideas)} ideas")
        print(f"   Idea-level parallelism: {self.max_workers} workers")
        print(f"   File-level parallelism: {self.processor.max_file_workers} workers per idea")
        print(f"{'='*80}\n")
        
        stats = {
            'total': len(ideas),
            'completed': 0,
            'failed': 0,
            'no_files': 0
        }
        
        # Process in parallel
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_idea = {
                executor.submit(self._process_single_idea, idea): idea
                for idea in ideas
            }
            
            # Process results with progress bar
            with tqdm(total=len(ideas), desc="Processing ideas") as pbar:
                for future in as_completed(future_to_idea):
                    idea = future_to_idea[future]
                    try:
                        result = future.result()
                        stats[result['status']] += 1
                    except Exception as e:
                        logger.error(f"Failed to process idea {idea['idea_id']}: {e}")
                        stats['failed'] += 1
                    
                    pbar.update(1)
        
        return stats

    def _process_single_idea(self, idea: Dict) -> Dict:
            
        """Process a single idea: extract files and insert to DB."""
        
        idea_id = str(idea['idea_id'])

        try:
            files_dir = self.additional_files_dir / idea_id
            extraction_result = self.processor.process_idea_files(idea_id, files_dir)

            db_record = {
                'idea_id': idea_id,
                'idea_title': idea.get('idea_title'),
                'brief_summary': idea.get('brief_summary'),
                'challenge_opportunity': idea.get('challenge_opportunity'),
                'novelty_benefits_risks': idea.get('novelty_benefits_risks'),
                'responsible_ai': idea.get('responsible_ai'),
                'additional_file_types': extraction_result.get('file_types'),
                'second_file': idea.get('second_file'),
                'preferred_week': idea.get('preferred_week'),
                'build_preference': idea.get('build_preference'),
                'build_approach': idea.get('build_approach'),
                'code_preference': idea.get('code_preference'),
                'extracted_files_content': extraction_result.get('extracted_content'),
                'files_processed': extraction_result.get('files_processed'),
                'content_type': extraction_result.get('content_type'),
                'extraction_status': extraction_result.get('status')
            }

            self.db_manager.insert_idea(db_record)

            return {
                'idea_id': idea_id,
                'status': extraction_result.get('status')
            }

        except Exception as e:
            logger.error(f"Error processing idea {idea_id}: {e}")

            error_record = {
                'idea_id': idea_id,
                'idea_title': idea.get('idea_title'),
                'extraction_status': 'failed',
                'error_message': str(e)
            }

            try:
                self.db_manager.insert_idea(error_record)
            except Exception:
                pass

            return {
                'idea_id': idea_id,
                'status': 'failed'
            }


    
    
