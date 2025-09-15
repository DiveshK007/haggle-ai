import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import os

class Database:
    """
    Simple SQLite database for storing negotiation results and savings ledger
    """
    
    def __init__(self, db_path: str = "haggle_ai.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Negotiations table - stores completed negotiation results
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS negotiations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    service_type TEXT NOT NULL,
                    vendor_message TEXT,
                    original_price REAL NOT NULL,
                    target_price REAL NOT NULL, 
                    final_price REAL NOT NULL,
                    savings REAL NOT NULL,
                    annual_savings REAL NOT NULL,
                    strategy TEXT NOT NULL,
                    proposal_content TEXT,
                    vendor_response TEXT,
                    success BOOLEAN NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Negotiation events table - for funnel analysis
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS negotiation_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    negotiation_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (negotiation_id) REFERENCES negotiations (id)
                )
            """)
            
            # Negotiation threads table - for tracking ongoing negotiations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS negotiation_threads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT UNIQUE NOT NULL,
                    context TEXT NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # User preferences/settings
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def save_negotiation(self, negotiation_data: Dict[str, Any]) -> int:
        """
        Save a completed negotiation to the database
        
        Args:
            negotiation_data: Dictionary containing negotiation results
            
        Returns:
            ID of the inserted record
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Convert datetime to string if needed
            date_str = negotiation_data.get('date')
            if isinstance(date_str, datetime):
                date_str = date_str.isoformat()
            
            cursor.execute("""
                INSERT INTO negotiations (
                    date, service_type, vendor_message, original_price, 
                    target_price, final_price, savings, annual_savings,
                    strategy, proposal_content, vendor_response, success
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                date_str,
                negotiation_data.get('service_type', ''),
                negotiation_data.get('vendor_message', ''),
                negotiation_data.get('original_price', 0),
                negotiation_data.get('target_price', 0),
                negotiation_data.get('final_price', 0),
                negotiation_data.get('savings', 0),
                negotiation_data.get('annual_savings', 0),
                negotiation_data.get('strategy', ''),
                negotiation_data.get('proposal_content', ''),
                negotiation_data.get('vendor_response', ''),
                negotiation_data.get('success', False)
            ))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_all_negotiations(self) -> List[Dict[str, Any]]:
        """
        Retrieve all negotiation records
        
        Returns:
            List of dictionaries containing negotiation data
        """
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row  # This allows dict-like access
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM negotiations 
                ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_negotiations_by_service(self, service_type: str) -> List[Dict[str, Any]]:
        """Get negotiations filtered by service type"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM negotiations 
                WHERE service_type = ?
                ORDER BY created_at DESC
            """, (service_type,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    
    def get_total_savings(self) -> Dict[str, float]:
        """
        Get total savings statistics
        
        Returns:
            Dictionary with total, monthly, and annual savings
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    SUM(savings) as total_monthly_savings,
                    SUM(annual_savings) as total_annual_savings,
                    COUNT(*) as total_negotiations,
                    AVG(savings) as avg_monthly_savings
                FROM negotiations
            """)
            
            result = cursor.fetchone()
            
            return {
                'total_monthly_savings': result[0] or 0,
                'total_annual_savings': result[1] or 0, 
                'total_negotiations': result[2] or 0,
                'avg_monthly_savings': result[3] or 0
            }
    
    def get_strategy_performance(self) -> Dict[str, Dict[str, Any]]:
        """
        Get performance statistics by negotiation strategy
        
        Returns:
            Dictionary with strategy performance data
        """
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    strategy,
                    COUNT(*) as usage_count,
                    AVG(savings) as avg_savings,
                    SUM(annual_savings) as total_annual_savings,
                    AVG(CAST(success AS FLOAT)) as success_rate
                FROM negotiations
                GROUP BY strategy
                ORDER BY avg_savings DESC
            """)
            
            results = cursor.fetchall()
            
            strategy_stats = {}
            for row in results:
                strategy_stats[row[0]] = {
                    'usage_count': row[1],
                    'avg_savings': round(row[2] or 0, 2),
                    'total_annual_savings': row[3] or 0,
                    'success_rate': round((row[4] or 0) * 100, 1)
                }
            
            return strategy_stats
    
    def save_negotiation_thread(self, thread_id: str, context: Dict[str, Any]) -> None:
        """Save an ongoing negotiation thread"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO negotiation_threads (
                    thread_id, context, updated_at
                ) VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (thread_id, json.dumps(context)))
            
            conn.commit()
    
    def get_negotiation_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a negotiation thread by ID"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM negotiation_threads 
                WHERE thread_id = ?
            """, (thread_id,))
            
            row = cursor.fetchone()
            if row:
                result = dict(row)
                result['context'] = json.loads(result['context'])
                return result
            
            return None

    def get_all_negotiation_threads(self) -> List[Dict[str, Any]]:
        """Retrieve all active negotiation threads"""
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM negotiation_threads
                WHERE status = 'active'
                ORDER BY updated_at DESC
            """)
            
            rows = cursor.fetchall()
            threads = []
            for row in rows:
                thread = dict(row)
                thread['context'] = json.loads(thread['context'])
                threads.append(thread)
            return threads
    
    def update_user_setting(self, key: str, value: str) -> None:
        """Update or insert a user setting"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO user_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            
            conn.commit()
    
    def get_user_setting(self, key: str, default: str = None) -> Optional[str]:
        """Get a user setting value"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT value FROM user_settings WHERE key = ?
            """, (key,))
            
            result = cursor.fetchone()
            return result[0] if result else default
    
    def export_to_csv(self, filename: str = None) -> str:
        """
        Export negotiations to CSV format
        
        Args:
            filename: Optional filename, if None generates timestamp-based name
            
        Returns:
            CSV filename that was created
        """
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"haggle_ai_export_{timestamp}.csv"
        
        negotiations = self.get_all_negotiations()
        
        if not negotiations:
            return ""
        
        # CSV header
        headers = [
            'Date', 'Service Type', 'Original Price', 'Final Price', 
            'Monthly Savings', 'Annual Savings', 'Strategy', 'Success'
        ]
        
        # Write CSV
        import csv
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for neg in negotiations:
                writer.writerow([
                    neg['date'],
                    neg['service_type'],
                    neg['original_price'],
                    neg['final_price'],
                    neg['savings'],
                    neg['annual_savings'],
                    neg['strategy'],
                    'Yes' if neg['success'] else 'No'
                ])
        
        return filename
    
    def clear_all_data(self) -> None:
        """Clear all data from the database (for testing/reset)"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM negotiations")
            cursor.execute("DELETE FROM negotiation_threads")
            cursor.execute("DELETE FROM user_settings")
            cursor.execute("DELETE FROM negotiation_events")
            
            conn.commit()
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get general database statistics"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get table sizes
            stats = {}
            
            cursor.execute("SELECT COUNT(*) FROM negotiations")
            stats['negotiations_count'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM negotiation_threads")
            stats['threads_count'] = cursor.fetchone()[0]
            
            # Get database file size
            if os.path.exists(self.db_path):
                stats['db_size_kb'] = round(os.path.getsize(self.db_path) / 1024, 2)
            else:
                stats['db_size_kb'] = 0
            
            return stats
    
    def log_event(self, negotiation_id: int, event_type: str) -> None:
        """Log a negotiation event for funnel analysis"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO negotiation_events (negotiation_id, event_type)
                VALUES (?, ?)
            """, (negotiation_id, event_type))
            
            conn.commit()
            
    def get_funnel_analysis(self) -> Dict[str, int]:
        """Get negotiation funnel analysis"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT event_type, COUNT(*)
                FROM negotiation_events
                GROUP BY event_type
            """)
            
            results = cursor.fetchall()
            
            return {row[0]: row[1] for row in results}

# Utility functions for database management
def backup_database(source_path: str = "haggle_ai.db", backup_path: str = None) -> str:
    """Create a backup of the database"""
    
    if not backup_path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"haggle_ai_backup_{timestamp}.db"
    
    if os.path.exists(source_path):
        import shutil
        shutil.copy2(source_path, backup_path)
        return backup_path
    else:
        raise FileNotFoundError(f"Source database {source_path} not found")

def restore_database(backup_path: str, target_path: str = "haggle_ai.db") -> None:
    """Restore database from backup"""
    
    if os.path.exists(backup_path):
        import shutil
        shutil.copy2(backup_path, target_path)
    else:
        raise FileNotFoundError(f"Backup file {backup_path} not found")

# Test the database functionality
if __name__ == "__main__":
    # Quick test of database functionality
    db = Database("test_haggle.db")
    
    # Test saving a negotiation
    test_data = {
        'date': datetime.now(),
        'service_type': 'SaaS Subscription',
        'original_price': 500,
        'target_price': 400, 
        'final_price': 450,
        'savings': 50,
        'annual_savings': 600,
        'strategy': 'polite',
        'success': True
    }
    
    nego_id = db.save_negotiation(test_data)
    print(f"✅ Saved negotiation with ID: {nego_id}")
    
    # Test retrieval
    negotiations = db.get_all_negotiations()
    print(f"✅ Retrieved {len(negotiations)} negotiations")
    
    # Test stats
    stats = db.get_total_savings()
    print(f"✅ Total savings: ${stats['total_annual_savings']}/year")
    
    # Cleanup test database
    os.remove("test_haggle.db")
    print("✅ Database test completed successfully!")
