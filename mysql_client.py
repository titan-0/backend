"""
MySQL client connection and operations
"""
import pymysql
from typing import Dict, Any
from config import MYSQL_CONFIG


class MySQLClient:
    """MySQL connection manager"""
    
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.connect()
    
    def connect(self):
        """Establish MySQL connection"""
        print(f"🔌 Connecting to MySQL at {MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}...")
        self.connection = pymysql.connect(
            host=MYSQL_CONFIG['host'],
            port=MYSQL_CONFIG['port'],
            user=MYSQL_CONFIG['user'],
            password=MYSQL_CONFIG['password'],
            database=MYSQL_CONFIG['database'],
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False
        )
        self.cursor = self.connection.cursor()
        print("✅ MySQL connection established")
    
    def insert_or_update(self, table_name: str, data_dict: Dict[str, Any]) -> bool:
        """
        Insert or update data into MySQL table using ON DUPLICATE KEY UPDATE.
        Returns True if successful, False otherwise.
        """
        if not data_dict:
            print("⚠️ No data to insert")
            return False
        
        try:
            columns = ', '.join([f"`{col}`" for col in data_dict.keys()])
            placeholders = ', '.join(['%s'] * len(data_dict))
            update_clause = ', '.join([f"`{col}`=VALUES(`{col}`)" for col in data_dict.keys()])
            
            insert_query = f"""
                INSERT INTO `{table_name}` ({columns})
                VALUES ({placeholders})
                ON DUPLICATE KEY UPDATE {update_clause}
            """
            
            self.cursor.execute(insert_query, list(data_dict.values()))
            self.connection.commit()
            return True
            
        except Exception as e:
            print(f"❌ MySQL insert failed: {e}")
            self.connection.rollback()
            return False
    
    def close(self):
        """Close MySQL connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
