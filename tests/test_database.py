"""Tests for database module."""
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.database import (
    Database,
    close_mongo_connection,
    connect_to_mongo,
    create_indexes,
    db,
    get_database,
)


class TestDatabase:
    """Test Database class."""

    def test_database_init(self):
        """Test Database class initialization."""
        database = Database()

        assert database.client is None
        assert database.database is None

    def test_get_client(self):
        """Test getting client from database."""
        database = Database()
        mock_client = MagicMock()
        database.client = mock_client

        assert database.get_client() == mock_client

    def test_get_database(self):
        """Test getting database from database instance."""
        database = Database()
        mock_database = MagicMock()
        database.database = mock_database

        assert database.get_database() == mock_database


class TestGetDatabase:
    """Test get_database dependency function."""

    def test_get_database_dependency(self):
        """Test get_database dependency function."""
        # Store original database
        original_db = db.database

        # Set mock database
        mock_database = MagicMock()
        db.database = mock_database

        result = get_database()
        assert result == mock_database

        # Restore original
        db.database = original_db


class TestConnectToMongo:
    """Test MongoDB connection functionality."""

    @pytest.mark.asyncio
    @patch("app.core.database.AsyncIOMotorClient")
    @patch("app.core.database.create_indexes")
    async def test_connect_to_mongo_success(
        self, mock_create_indexes, mock_client_class
    ):
        """Test successful MongoDB connection."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_client_class.return_value = mock_client
        mock_create_indexes.return_value = None

        # Mock database
        mock_database = MagicMock()
        mock_client.__getitem__ = MagicMock(return_value=mock_database)

        # Store original db values
        original_client = db.client
        original_database = db.database

        try:
            await connect_to_mongo()

            # Verify client was created correctly
            mock_client_class.assert_called_once()

            # Verify ping was called
            mock_client.admin.command.assert_called_once_with("ping")

            # Verify create_indexes was called
            mock_create_indexes.assert_called_once()

            # Verify db was set
            assert db.client == mock_client

        finally:
            # Restore original values
            db.client = original_client
            db.database = original_database

    @pytest.mark.asyncio
    @patch("app.core.database.AsyncIOMotorClient")
    async def test_connect_to_mongo_connection_failure(self, mock_client_class):
        """Test MongoDB connection failure."""
        # Setup mock to raise exception
        mock_client_class.side_effect = Exception("Connection failed")

        # Store original db values
        original_client = db.client
        original_database = db.database

        try:
            with pytest.raises(Exception, match="Connection failed"):
                await connect_to_mongo()
        finally:
            # Restore original values
            db.client = original_client
            db.database = original_database

    @pytest.mark.asyncio
    @patch("app.core.database.AsyncIOMotorClient")
    async def test_connect_to_mongo_ping_failure(self, mock_client_class):
        """Test MongoDB connection with ping failure."""
        # Setup mocks
        mock_client = AsyncMock()
        mock_client.admin.command = AsyncMock(side_effect=Exception("Ping failed"))
        mock_client_class.return_value = mock_client

        # Store original db values
        original_client = db.client
        original_database = db.database

        try:
            with pytest.raises(Exception, match="Ping failed"):
                await connect_to_mongo()
        finally:
            # Restore original values
            db.client = original_client
            db.database = original_database


class TestCloseMongConnection:
    """Test MongoDB connection closing."""

    @pytest.mark.asyncio
    async def test_close_mongo_connection_success(self):
        """Test successful MongoDB connection closing."""
        # Setup mock client
        mock_client = MagicMock()
        mock_client.close = MagicMock()

        # Store original client
        original_client = db.client
        db.client = mock_client

        try:
            await close_mongo_connection()

            # Verify close was called
            mock_client.close.assert_called_once()
        finally:
            # Restore original client
            db.client = original_client

    @pytest.mark.asyncio
    async def test_close_mongo_connection_no_client(self):
        """Test closing connection when no client exists."""
        # Store original client
        original_client = db.client
        db.client = None

        try:
            # Should not raise exception
            await close_mongo_connection()
        finally:
            # Restore original client
            db.client = original_client

    @pytest.mark.asyncio
    async def test_close_mongo_connection_error(self):
        """Test error during connection closing."""
        # Setup mock client that raises error
        mock_client = MagicMock()
        mock_client.close = MagicMock(side_effect=Exception("Close failed"))

        # Store original client
        original_client = db.client
        db.client = mock_client

        try:
            # Should not raise exception, just log error
            await close_mongo_connection()

            # Verify close was attempted
            mock_client.close.assert_called_once()
        finally:
            # Restore original client
            db.client = original_client


class TestCreateIndexes:
    """Test database index creation."""

    @pytest.mark.asyncio
    async def test_create_indexes_success(self):
        """Test successful index creation."""
        # Setup mock database with collections
        mock_database = MagicMock()

        # Mock collections
        collections = [
            "users",
            "environments",
            "sessions",
            "clusters",
            "templates",
            "environment_metrics",
        ]

        for collection_name in collections:
            collection_mock = AsyncMock()
            collection_mock.create_index = AsyncMock(return_value="index_name")
            setattr(mock_database, collection_name, collection_mock)

        # Store original database
        original_database = db.database
        db.database = mock_database

        try:
            await create_indexes()

            # Verify indexes were created for users collection
            mock_database.users.create_index.assert_any_call("email", unique=True)
            mock_database.users.create_index.assert_any_call("username", unique=True)
            mock_database.users.create_index.assert_any_call("google_id")

            # Verify indexes were created for environments collection
            mock_database.environments.create_index.assert_any_call("user_id")
            mock_database.environments.create_index.assert_any_call(
                [("user_id", 1), ("status", 1)]
            )

            # Verify sessions collection TTL index
            mock_database.sessions.create_index.assert_any_call(
                "expires_at", expireAfterSeconds=0
            )

            # Verify templates collection indexes
            mock_database.templates.create_index.assert_any_call("name", unique=True)
            mock_database.templates.create_index.assert_any_call("category")

        finally:
            # Restore original database
            db.database = original_database

    @pytest.mark.asyncio
    async def test_create_indexes_error(self):
        """Test error during index creation."""
        # Setup mock database that raises error
        mock_database = MagicMock()
        mock_users = AsyncMock()
        mock_users.create_index = AsyncMock(
            side_effect=Exception("Index creation failed")
        )
        mock_database.users = mock_users

        # Store original database
        original_database = db.database
        db.database = mock_database

        try:
            # Should not raise exception, just log error
            await create_indexes()

            # Verify create_index was attempted
            mock_users.create_index.assert_called()

        finally:
            # Restore original database
            db.database = original_database
