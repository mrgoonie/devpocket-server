#!/usr/bin/env python3

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.user import UserCreate, UserInDB
from app.core.database import get_database
from app.services.auth_service import AuthService

async def test_user_creation():
    """Test user creation directly"""
    
    # Test UserCreate model validation
    try:
        user_data = UserCreate(
            username="testdirect",
            email="testdirect@example.com", 
            password="TestPass123",
            full_name="Test Direct"
        )
        print("✓ UserCreate model validation passed")
        print(f"User data: {user_data}")
    except Exception as e:
        print(f"✗ UserCreate model validation failed: {e}")
        return
    
    # Test UserInDB model creation
    try:
        user_db_data = {
            "_id": "507f1f77bcf86cd799439011",  # Valid ObjectId string
            "username": "testdirect",
            "email": "testdirect@example.com",
            "full_name": "Test Direct",
            "hashed_password": "hashed_pass",
            "is_active": True,
            "is_verified": False,
            "subscription_plan": "free",
            "created_at": "2023-01-01T00:00:00",
            "updated_at": "2023-01-01T00:00:00",
            "failed_login_attempts": 0
        }
        
        user_in_db = UserInDB(**user_db_data)
        print("✓ UserInDB model validation passed")
        print(f"User in DB: {user_in_db}")
        print(f"User ID type: {type(user_in_db.id)}")
        print(f"User ID value: {user_in_db.id}")
    except Exception as e:
        print(f"✗ UserInDB model validation failed: {e}")
        return
    
    # Test database connection and service
    try:
        db = await get_database()
        print("✓ Database connection successful")
        
        auth_service = AuthService()
        auth_service.set_database(db)
        
        # Try to create user through service
        result = await auth_service.create_user(user_data)
        print("✓ User creation through service successful")
        print(f"Created user: {result}")
        
    except Exception as e:
        print(f"✗ Service user creation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_user_creation())