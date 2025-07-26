#!/usr/bin/env python3
"""
Script to reset selected collections in the DevPocket database.
This script allows selective deletion of collections with confirmation prompts.

Usage:
    python scripts/reset_collections.py
    ENV_FILE=.env.prod python scripts/reset_collections.py
"""

import asyncio
import os
import sys
from typing import List, Dict, Any

# Add the parent directory to the path so we can import our app modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.core.database import create_indexes
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Available collections that can be reset
AVAILABLE_COLLECTIONS = {
    "environments": "Development environments and their data",
    "sessions": "WebSocket and user sessions",
    "environment_metrics": "Environment usage metrics and logs",
    "users": "User accounts and authentication data (⚠️  DESTRUCTIVE)",
    "templates": "Environment templates (⚠️  Will remove custom templates)",
    "clusters": "Kubernetes cluster configurations (⚠️  CRITICAL)"
}

# Collections that require extra confirmation due to their critical nature
CRITICAL_COLLECTIONS = {"users", "templates", "clusters"}

class DatabaseResetter:
    def __init__(self):
        self.client: AsyncIOMotorClient = None
        self.db = None
    
    async def connect(self):
        """Connect to the database."""
        try:
            self.client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.db = self.client[settings.DATABASE_NAME]
            
            # Test connection
            await self.client.admin.command("ping")
            logger.info(f"Connected to MongoDB: {settings.DATABASE_NAME}")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def close(self):
        """Close database connection."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def list_collection_stats(self, collections: List[str]) -> Dict[str, Any]:
        """Get statistics for the specified collections."""
        stats = {}
        
        for collection_name in collections:
            try:
                collection = self.db[collection_name]
                count = await collection.count_documents({})
                stats[collection_name] = {
                    "count": count,
                    "exists": count > 0
                }
            except Exception as e:
                stats[collection_name] = {
                    "count": 0,
                    "exists": False,
                    "error": str(e)
                }
        
        return stats
    
    async def reset_collections(self, collections: List[str]) -> Dict[str, Any]:
        """Reset the specified collections."""
        results = {}
        
        for collection_name in collections:
            try:
                collection = self.db[collection_name]
                
                # Get count before deletion
                count_before = await collection.count_documents({})
                
                # Drop the collection
                await collection.drop()
                
                results[collection_name] = {
                    "success": True,
                    "documents_deleted": count_before,
                    "message": f"Collection '{collection_name}' reset successfully"
                }
                
                logger.info(f"Reset collection '{collection_name}' - {count_before} documents deleted")
                
            except Exception as e:
                results[collection_name] = {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to reset collection '{collection_name}'"
                }
                logger.error(f"Failed to reset collection '{collection_name}': {e}")
        
        return results
    
    async def recreate_indexes(self):
        """Recreate database indexes after collection reset."""
        try:
            # Temporarily set the global database for index creation
            from app.core.database import db as global_db
            old_database = global_db.database
            global_db.database = self.db
            
            await create_indexes()
            
            # Restore the original database
            global_db.database = old_database
            
            logger.info("Database indexes recreated successfully")
            
        except Exception as e:
            logger.error(f"Failed to recreate indexes: {e}")
            raise

def display_collections():
    """Display available collections with descriptions."""
    print("\n📋 Available collections to reset:")
    print("=" * 60)
    
    for i, (name, description) in enumerate(AVAILABLE_COLLECTIONS.items(), 1):
        warning = " 🚨" if name in CRITICAL_COLLECTIONS else ""
        print(f"{i:2d}. {name:<20} - {description}{warning}")
    
    print(f"{len(AVAILABLE_COLLECTIONS) + 1:2d}. all                 - Reset ALL collections (⚠️  VERY DESTRUCTIVE)")
    print("=" * 60)

def get_user_selection() -> List[str]:
    """Get user selection of collections to reset."""
    display_collections()
    
    while True:
        try:
            selection = input("\nEnter collection numbers (comma-separated) or 'q' to quit: ").strip()
            
            if selection.lower() == 'q':
                return []
            
            # Parse selection
            if selection == str(len(AVAILABLE_COLLECTIONS) + 1):
                # Select all collections
                return list(AVAILABLE_COLLECTIONS.keys())
            
            indices = [int(x.strip()) for x in selection.split(',')]
            collection_names = list(AVAILABLE_COLLECTIONS.keys())
            
            selected = []
            for idx in indices:
                if 1 <= idx <= len(collection_names):
                    selected.append(collection_names[idx - 1])
                else:
                    print(f"❌ Invalid selection: {idx}")
                    continue
            
            if not selected:
                print("❌ No valid collections selected")
                continue
            
            return selected
            
        except ValueError:
            print("❌ Invalid input. Please enter numbers separated by commas.")
        except KeyboardInterrupt:
            print("\n\n👋 Operation cancelled by user")
            return []

def confirm_reset(collections: List[str], stats: Dict[str, Any]) -> bool:
    """Confirm the reset operation with the user."""
    print("\n🔍 Selected collections to reset:")
    print("=" * 50)
    
    total_documents = 0
    has_critical = False
    
    for collection in collections:
        stat = stats.get(collection, {})
        count = stat.get("count", 0)
        total_documents += count
        
        warning = "🚨 CRITICAL" if collection in CRITICAL_COLLECTIONS else ""
        print(f"• {collection:<20} - {count:,} documents {warning}")
        
        if collection in CRITICAL_COLLECTIONS:
            has_critical = True
    
    print("=" * 50)
    print(f"📊 Total documents to delete: {total_documents:,}")
    
    if has_critical:
        print("\n⚠️  WARNING: You have selected CRITICAL collections!")
        print("   This action will delete important system data and cannot be undone.")
    
    print(f"\n🗄️  Database: {settings.DATABASE_NAME}")
    print(f"🔗 MongoDB URL: {settings.MONGODB_URL}")
    
    # First confirmation
    confirm1 = input(f"\n❓ Are you sure you want to reset these {len(collections)} collections? (type 'yes' to continue): ")
    if confirm1.lower() != 'yes':
        return False
    
    # Extra confirmation for critical collections
    if has_critical:
        print("\n🚨 FINAL WARNING: Critical collections selected!")
        confirm2 = input("❓ Type 'DELETE' in uppercase to confirm deletion of critical data: ")
        if confirm2 != 'DELETE':
            return False
    
    return True

async def main():
    """Main function to handle collection reset."""
    print("🗃️  DevPocket Database Collection Reset Tool")
    print("=" * 50)
    
    # Check environment
    env_file = os.getenv('ENV_FILE', '.env')
    print(f"📁 Using environment file: {env_file}")
    print(f"🗄️  Target database: {settings.DATABASE_NAME}")
    print(f"🔗 MongoDB URL: {settings.MONGODB_URL}")
    
    # Get user selection
    selected_collections = get_user_selection()
    
    if not selected_collections:
        print("👋 No collections selected. Exiting...")
        return
    
    # Initialize database connection
    resetter = DatabaseResetter()
    
    try:
        await resetter.connect()
        
        # Get collection statistics
        print("\n📊 Gathering collection statistics...")
        stats = await resetter.list_collection_stats(selected_collections)
        
        # Confirm reset operation
        if not confirm_reset(selected_collections, stats):
            print("❌ Operation cancelled by user")
            return
        
        # Perform reset
        print(f"\n🔄 Resetting {len(selected_collections)} collections...")
        results = await resetter.reset_collections(selected_collections)
        
        # Display results
        print("\n📋 Reset Results:")
        print("=" * 40)
        
        successful = 0
        failed = 0
        total_deleted = 0
        
        for collection, result in results.items():
            if result['success']:
                successful += 1
                deleted = result.get('documents_deleted', 0)
                total_deleted += deleted
                print(f"✅ {collection}: {deleted:,} documents deleted")
            else:
                failed += 1
                print(f"❌ {collection}: {result['message']}")
        
        print("=" * 40)
        print(f"📊 Summary: {successful} successful, {failed} failed")
        print(f"🗑️  Total documents deleted: {total_deleted:,}")
        
        # Recreate indexes if any collections were reset
        if successful > 0:
            print("\n🔧 Recreating database indexes...")
            await resetter.recreate_indexes()
            print("✅ Database indexes recreated")
        
        print("\n✨ Database reset operation completed!")
        
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        print(f"\n❌ Operation failed: {e}")
        return 1
    
    finally:
        await resetter.close()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)