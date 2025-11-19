import psycopg2
from psycopg2.extras import execute_batch
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Handle all database operations."""
    
    def __init__(self, db_config: dict, table_name: str):
        self.db_config = db_config
        self.table_name = table_name
        self.connection = None
    
    def connect(self):
        """Establish database connection."""
        self.connection = psycopg2.connect(**self.db_config)
        logger.info("✓ Database connected")
    
    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            logger.info("✓ Database connection closed")
    
    def insert_idea(self, idea_data: Dict):
        """Insert single idea with extracted content."""
        columns = list(idea_data.keys())
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        
        sql = f"""
        INSERT INTO {self.table_name} ({column_names})
        VALUES ({placeholders})
        ON CONFLICT (idea_id) DO UPDATE SET
            extracted_files_content = EXCLUDED.extracted_files_content,
            files_processed = EXCLUDED.files_processed,
            extraction_status = EXCLUDED.extraction_status,
            updated_at = CURRENT_TIMESTAMP
        """
        
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, list(idea_data.values()))
            self.connection.commit()
            logger.info(f"✓ Inserted idea {idea_data.get('idea_id')}")
        except Exception as e:
            self.connection.rollback()
            logger.error(f"✗ Failed to insert idea: {e}")
            raise
        finally:
            cursor.close()
    
    def insert_batch(self, ideas: List[Dict], batch_size: int = 50):
        """Batch insert multiple ideas."""
        if not ideas:
            return
        
        # Prepare batch insert
        columns = list(ideas[0].keys())
        column_names = ', '.join(columns)
        placeholders = ', '.join(['%s'] * len(columns))
        
        sql = f"""
        INSERT INTO {self.table_name} ({column_names})
        VALUES ({placeholders})
        ON CONFLICT (idea_id) DO UPDATE SET
            extracted_files_content = EXCLUDED.extracted_files_content,
            files_processed = EXCLUDED.files_processed,
            extraction_status = EXCLUDED.extraction_status,
            updated_at = CURRENT_TIMESTAMP
        """
        
        cursor = self.connection.cursor()
        try:
            execute_batch(cursor, sql, [list(idea.values()) for idea in ideas], page_size=batch_size)
            self.connection.commit()
            logger.info(f"✓ Inserted {len(ideas)} ideas in batch")
        except Exception as e:
            self.connection.rollback()
            logger.error(f"✗ Batch insert failed: {e}")
            raise
        finally:
            cursor.close()
    
    def get_statistics(self) -> Dict:
        """Get processing statistics."""
        cursor = self.connection.cursor()
        try:
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT(CASE WHEN extraction_status = 'completed' THEN 1 END) as completed,
                    COUNT(CASE WHEN extraction_status = 'failed' THEN 1 END) as failed,
                    COUNT(CASE WHEN extraction_status = 'no_files' THEN 1 END) as no_files,
                    COUNT(CASE WHEN classification_status = 'completed' THEN 1 END) as classified,
                    COUNT(CASE WHEN classification_status = 'failed' THEN 1 END) as classification_failed
                FROM {self.table_name}
            """)
            result = cursor.fetchone()
            return {
                'total': result[0],
                'completed': result[1],
                'failed': result[2],
                'no_files': result[3],
                'classified': result[4],
                'classification_failed': result[5]
            }
        finally:
            cursor.close()
