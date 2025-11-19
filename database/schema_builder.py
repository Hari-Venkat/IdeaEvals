import json
from pathlib import Path
import psycopg2


class SchemaBuilder:
    """Build database schema from JSON definition."""
    
    def __init__(self, schema_file: Path, db_config: dict):
        self.schema_file = schema_file
        self.db_config = db_config
        self.schema = self._load_schema()
    
    def _load_schema(self) -> dict:
        """Load schema from JSON file."""
        with open(self.schema_file, 'r') as f:
            return json.load(f)
    
    def create_table(self):
        """Create table based on schema definition."""
        table_name = self.schema['table_name']
        columns = self.schema['columns']
        
        # Build CREATE TABLE SQL
        column_defs = []
        for col in columns:
            col_def = f"{col['name']} {col['type']}"
            if 'constraints' in col:
                col_def += f" {col['constraints']}"
            if 'default' in col:
                col_def += f" DEFAULT {col['default']}"
            column_defs.append(col_def)
        
        sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            {', '.join(column_defs)}
        );
        
        CREATE INDEX IF NOT EXISTS idx_{table_name}_status 
        ON {table_name}(extraction_status);
        
        CREATE INDEX IF NOT EXISTS idx_{table_name}_idea_id 
        ON {table_name}(idea_id);
        """
        
        # Execute
        conn = psycopg2.connect(**self.db_config)
        cursor = conn.cursor()
        
        try:
            cursor.execute(sql)
            conn.commit()
            print(f"✓ Table '{table_name}' created successfully")
        except Exception as e:
            conn.rollback()
            print(f"✗ Failed to create table: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def get_column_names(self) -> list:
        """Get list of column names from schema."""
        return [col['name'] for col in self.schema['columns']]
