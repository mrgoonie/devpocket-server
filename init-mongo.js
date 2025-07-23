// MongoDB initialization script
db = db.getSiblingDB('devpocket');

// Create application user
db.createUser({
  user: 'devpocket_user',
  pwd: 'devpocket_password',
  roles: [
    {
      role: 'readWrite',
      db: 'devpocket'
    }
  ]
});

// Create collections with validation
db.createCollection('users', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['username', 'email', 'hashed_password', 'created_at'],
      properties: {
        username: {
          bsonType: 'string',
          minLength: 3,
          maxLength: 30
        },
        email: {
          bsonType: 'string',
          pattern: '^.+@.+\..+$'
        },
        hashed_password: {
          bsonType: 'string'
        },
        is_active: {
          bsonType: 'bool'
        },
        is_verified: {
          bsonType: 'bool'
        },
        subscription_plan: {
          bsonType: 'string',
          enum: ['free', 'starter', 'pro', 'admin']
        },
        created_at: {
          bsonType: 'date'
        }
      }
    }
  }
});

db.createCollection('environments', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['user_id', 'name', 'template', 'status', 'created_at'],
      properties: {
        user_id: {
          bsonType: 'string'
        },
        name: {
          bsonType: 'string',
          minLength: 1,
          maxLength: 50
        },
        template: {
          bsonType: 'string',
          enum: ['python', 'nodejs', 'golang', 'rust', 'ubuntu', 'custom']
        },
        status: {
          bsonType: 'string',
          enum: ['creating', 'running', 'stopped', 'terminated', 'error']
        },
        created_at: {
          bsonType: 'date'
        }
      }
    }
  }
});

db.createCollection('websocket_sessions');
db.createCollection('environment_metrics');

// Create indexes
db.users.createIndex({ 'email': 1 }, { unique: true });
db.users.createIndex({ 'username': 1 }, { unique: true });
db.users.createIndex({ 'google_id': 1 }, { sparse: true });

db.environments.createIndex({ 'user_id': 1 });
db.environments.createIndex({ 'user_id': 1, 'status': 1 });
db.environments.createIndex({ 'created_at': 1 });

db.websocket_sessions.createIndex({ 'user_id': 1 });
db.websocket_sessions.createIndex({ 'environment_id': 1 });
db.websocket_sessions.createIndex({ 'connection_id': 1 }, { unique: true });

db.environment_metrics.createIndex({ 'environment_id': 1, 'timestamp': 1 });
db.environment_metrics.createIndex({ 'timestamp': 1 }, { expireAfterSeconds: 2592000 }); // 30 days TTL

print('MongoDB initialization completed successfully');