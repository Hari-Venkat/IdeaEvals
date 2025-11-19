#!/usr/bin/env python3
"""
Complete Hackathon Evaluation Pipeline
Extraction → Classification → Evaluation

"""

import sys
import logging
from pathlib import Path
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

sys.path.insert(0, str(Path(__file__).parent))

from config.config import (
    DB_CONFIG, GEMINI_API_KEY, GEMINI_MODEL,
    DATA_DIR, ADDITIONAL_FILES_DIR, SCHEMA_FILE,
    BATCH_SIZE, MAX_FILE_WORKERS, LOG_FILE, LOG_LEVEL
)
from pipeline.csv_loader import CSVLoader
from extraction.file_extractor import FileExtractor
from database.schema_builder import SchemaBuilder
from database.db_manager import DatabaseManager
from pipeline.orchestrator import PipelineOrchestrator
from classification.tcs_classifier import TCSClassifier
from pipeline.classification_pipeline import ClassificationPipeline
from evaluation.idea_evaluator import IdeaEvaluator
from pipeline.evaluation_pipeline import EvaluationPipeline

# Logging setup
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)


def ensure_database_exists(db_config: dict):
    """Create database if it doesn't exist"""
    target_db = db_config['database']
    temp_config = db_config.copy()
    temp_config['database'] = 'postgres'
    
    try:
        conn = psycopg2.connect(**temp_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
        exists = cursor.fetchone()
        
        if exists:
            print(f"✓ Database '{target_db}' already exists")
        else:
            cursor.execute(f'CREATE DATABASE {target_db}')
            print(f"✓ Database '{target_db}' created successfully")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def check_prerequisites():
    """Check prerequisites"""
    issues = []
    
    csv_file = DATA_DIR / "ideas.xlsx"
    if not csv_file.exists():
        issues.append(f"❌ CSV file not found: {csv_file}")
    
    if not ADDITIONAL_FILES_DIR.exists():
        ADDITIONAL_FILES_DIR.mkdir(parents=True, exist_ok=True)
    
    if not SCHEMA_FILE.exists():
        issues.append(f"❌ Schema file not found: {SCHEMA_FILE}")
    
    if not GEMINI_API_KEY:
        issues.append("❌ Gemini API key not configured")
    
    if issues:
        print("\n⚠️  Prerequisites check failed:\n")
        for issue in issues:
            print(issue)
        return False
    
    return True


def main():
    """Main pipeline execution"""
    
    print("\n" + "="*80)
    print("🎯 HACKATHON EVALUATION PIPELINE")
    print("="*80 + "\n")
    
    print("🔍 Step 0: Checking prerequisites...")
    if not check_prerequisites():
        return 1
    print("✓ All prerequisites met\n")
    
    print("🗄️  Step 0.5: Ensuring database exists...")
    if not ensure_database_exists(DB_CONFIG):
        return 1
    print()
    
    # Uncomment this when you want to create rubrics table
    # create_rubrics_table_if_needed()
    
    try:
        # Step 1: Schema
        print("📋 Step 1: Creating database schema...")
        schema_builder = SchemaBuilder(SCHEMA_FILE, DB_CONFIG)
        schema_builder.create_table()
        table_name = schema_builder.schema['table_name']
        print()
        
        # Step 2: Load CSV
        print("📊 Step 2: Loading CSV/Excel data...")
        csv_file = DATA_DIR / "ideas.xlsx"
        csv_loader = CSVLoader(csv_file)
        df = csv_loader.load()
        df = csv_loader.normalize_columns()
        ideas = csv_loader.to_dict_list()
        print(f"✓ Loaded {len(ideas)} ideas\n")
        
        # Step 3: Initialize
        print("🔧 Step 3: Initializing extraction components...")
        extractor = FileExtractor(GEMINI_API_KEY, GEMINI_MODEL)
        db_manager = DatabaseManager(DB_CONFIG, table_name)
        db_manager.connect()
        print("✓ Components initialized\n")
        
        # Step 4: Extract
        print("⚙️  Step 4: Processing ideas and extracting files...")
        orchestrator = PipelineOrchestrator(
            extractor=extractor,
            db_manager=db_manager,
            additional_files_dir=ADDITIONAL_FILES_DIR,
            max_workers=BATCH_SIZE,
            max_file_workers=MAX_FILE_WORKERS,
            api_key=GEMINI_API_KEY
        )
        extraction_stats = orchestrator.process_all_ideas(ideas)
        
        # Step 5: Classify
        print("\n🎨 Step 5: Classifying themes, industries, and technologies...")
        classifier = TCSClassifier(api_key=GEMINI_API_KEY)
        classification_pipeline = ClassificationPipeline(
            classifier=classifier,
            db_manager=db_manager,
            max_workers=BATCH_SIZE
        )
        classification_stats = classification_pipeline.classify_all_ideas()
        
        # Step 6: Evaluate
        print("\n📊 Step 6: Evaluating ideas using TCS rubric...")
        evaluator = IdeaEvaluator(api_key=GEMINI_API_KEY)
        evaluation_pipeline = EvaluationPipeline(
            evaluator=evaluator,
            db_manager=db_manager,
            max_workers=8  # ✅ 8 threads for evaluation
        )
        evaluation_stats = evaluation_pipeline.evaluate_all_ideas()
        
        # Results
        print("\n" + "="*80)
        print("📊 PIPELINE RESULTS")
        print("="*80)
        
        print(f"\n📁 Extraction:")
        print(f"  Total ideas: {extraction_stats['total']}")
        print(f"  ✓ Completed: {extraction_stats['completed']}")
        print(f"  ⚠️  No files: {extraction_stats['no_files']}")
        print(f"  ✗ Failed: {extraction_stats['failed']}")
        
        print(f"\n🎨 Classification:")
        print(f"  Total classified: {classification_stats['total']}")
        print(f"  ✓ Completed: {classification_stats['completed']}")
        print(f"  ✗ Failed: {classification_stats['failed']}")
        
        print(f"\n📊 Evaluation:")
        print(f"  Total evaluated: {evaluation_stats['total']}")
        print(f"  ✓ Completed: {evaluation_stats['completed']}")
        print(f"  ✗ Failed: {evaluation_stats['failed']}")
        
        print("\n✅ Pipeline completed successfully!")
        print(f"📍 Database: {DB_CONFIG['database']}")
        print(f"📍 Table: {table_name}")
        
        # Show top ideas
        cursor = db_manager.connection.cursor()
        cursor.execute("""
            SELECT idea_id, idea_title, weighted_total_score, investment_recommendation
            FROM hackathon_ideas
            WHERE evaluation_status = 'completed'
            ORDER BY weighted_total_score DESC
            LIMIT 3
        """)
        
        print(f"\n🏆 Top 3 Ideas:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1][:50]}... - Score: {row[2]:.1f}/10 ({row[3]})")
        
        cursor.close()
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\n✗ Pipeline failed: {e}")
        return 1
    
    finally:
        if 'db_manager' in locals():
            db_manager.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
