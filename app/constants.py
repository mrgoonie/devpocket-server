"""
Constants used throughout the application.
"""

from bson import ObjectId

# System user ObjectId - used for system-created items like default templates and clusters
# This is a fixed ObjectId that represents the "system" user
SYSTEM_USER_ID = ObjectId("000000000000000000000001")

# Other system constants
DEFAULT_SYSTEM_USERNAME = "system"
