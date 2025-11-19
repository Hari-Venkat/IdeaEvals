import pandas as pd
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class CSVLoader:
    """Load and parse CSV/Excel files."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.df = None
    
    def load(self) -> pd.DataFrame:
        """Load CSV or Excel file."""
        try:
            if self.file_path.suffix.lower() in ['.xlsx', '.xls']:
                self.df = pd.read_excel(self.file_path)
            else:
                self.df = pd.read_csv(self.file_path)
            
            logger.info(f"✓ Loaded {len(self.df)} rows from {self.file_path.name}")
            return self.df
        
        except Exception as e:
            logger.error(f"✗ Failed to load file: {e}")
            raise
    
    def normalize_columns(self) -> pd.DataFrame:  # ✅ Fixed indentation - inside class
        """Normalize column names to match database schema."""
        column_mapping = {
            'Idea Id': 'idea_id',
            'Your idea title': 'idea_title',
            'Brief summary of your Idea': 'brief_summary',
            'Challenge/Business opportunity being addressed and the ability to scale it across TCS and multiple customers.': 'challenge_opportunity',
            'Novelty of the idea, benefits and risks.': 'novelty_benefits_risks',
            'Highlight adherence to Responsible AI principles such as Security, Fairness, Privacy & Legal compliance.': 'responsible_ai',
            'Incase you have a second file that could further illustrate your solution, kindly upload the same here.': 'second_file',
            'Your preferred week of participation': 'preferred_week',
            'Your preference for Build Phase': 'build_preference',
            'Your preference on how you want to  build your idea': 'build_approach',
            'Your preference if you were to develop code': 'code_preference'
        }
        
        self.df = self.df.rename(columns=column_mapping)
        logger.info("✓ Column names normalized")
        return self.df
    
    def to_dict_list(self) -> List[Dict]:
        """Convert DataFrame to list of dictionaries."""
        # Replace NaN with None
        self.df = self.df.where(pd.notnull(self.df), None)
        return self.df.to_dict('records')
    
    def get_idea_ids(self) -> List[str]:
        """Get list of all idea IDs."""
        return self.df['idea_id'].astype(str).tolist()
