#!/usr/bin/env python3
"""
Debug script to analyze templates endpoint issue.
"""

import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.core.config import settings
from app.models.template import TemplateResponse, TemplateStatus


async def debug_templates():
    """Debug the templates collection to understand why only 1 item is returned"""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client.devpocket
    
    try:
        # Get total count
        total_count = await db.templates.count_documents({})
        print(f"Total templates in database: {total_count}")
        
        # Get all templates
        cursor = db.templates.find({}).sort("created_at", 1)
        templates = []
        
        print("\n=== Raw Template Data ===")
        async for template_data in cursor:
            print(f"\nTemplate ID: {template_data.get('_id')}")
            print(f"Name: {template_data.get('name')}")
            print(f"Status: {template_data.get('status')}")
            print(f"Category: {template_data.get('category')}")
            print(f"Created: {template_data.get('created_at')}")
            
            # Try to convert to TemplateResponse
            try:
                template_dict = dict(template_data)
                template_dict["id"] = str(template_dict.pop("_id"))
                template_response = TemplateResponse(**template_dict)
                templates.append(template_response)
                print(f"✓ Successfully converted to TemplateResponse")
            except Exception as e:
                print(f"✗ Error converting to TemplateResponse: {e}")
                print(f"  Missing or invalid fields: {e}")
        
        print(f"\n=== Conversion Summary ===")
        print(f"Successfully converted: {len(templates)} out of {total_count}")
        
        # Check status filtering
        active_templates = [t for t in templates if t.status != TemplateStatus.DEPRECATED]
        print(f"Active templates (non-deprecated): {len(active_templates)}")
        
        deprecated_templates = [t for t in templates if t.status == TemplateStatus.DEPRECATED]
        print(f"Deprecated templates: {len(deprecated_templates)}")
        
        # Show template details
        print(f"\n=== Template Details ===")
        for i, template in enumerate(templates, 1):
            print(f"{i}. {template.name} ({template.status}) - {template.display_name}")
        
    except Exception as e:
        print(f"Error during debug: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        client.close()


if __name__ == "__main__":
    asyncio.run(debug_templates())