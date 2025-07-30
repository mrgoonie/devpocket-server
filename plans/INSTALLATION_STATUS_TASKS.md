# Installation Status WebSocket Updates - Implementation Plan

## Overview
Stream real-time installation logs via WebSocket when environments are being created.

## Tasks

### 1. Add Installation Status to Environment Model
- [ ] Add `INSTALLING` status to EnvironmentStatus enum
- [ ] Add `installation_completed` boolean field

### 2. Create Pod Log Streaming Service
- [ ] Add method to stream pod logs using Kubernetes API
- [ ] Stream logs from container startup until installation completes
- [ ] Detect when installation is complete (e.g., when "sleep infinity" is reached)

### 3. Implement WebSocket Log Broadcasting
- [ ] Add method to WebSocketConnectionManager to send logs to all user connections
- [ ] Create installation log message format
- [ ] Stream raw logs as they appear in the container

### 4. Update Environment Creation Flow
- [ ] Modify _create_container to start log streaming after pod creation
- [ ] Set initial status to INSTALLING after pod is scheduled
- [ ] Transition to RUNNING only after installation completes
- [ ] Start log streaming task that monitors and broadcasts logs

### 5. Handle Edge Cases
- [ ] Add timeout for installation (e.g., 10 minutes)
- [ ] Handle pod failures during installation
- [ ] Support reconnecting WebSocket clients to resume log streaming
- [ ] Clean up log streaming when installation completes

## Technical Approach

### Log Streaming Implementation
- Use Kubernetes API to follow pod logs (`follow=True`)
- Stream each log line directly to WebSocket clients
- No parsing needed - send raw installation output
- Monitor for completion signal (e.g., specific log pattern or timeout)

## Message Format
```json
{
  "type": "installation_log",
  "environment_id": "...",
  "data": "Get:1 http://archive.ubuntu.com/ubuntu jammy InRelease [270 kB]\n",
  "timestamp": "2024-01-20T10:30:45Z"
}
```

## Completion Message
```json
{
  "type": "installation_complete",
  "environment_id": "...",
  "status": "running"
}
```

## Implementation Priority
1. Add Kubernetes log streaming capability
2. Implement WebSocket broadcasting for logs
3. Add installation status tracking
4. Test with different templates
5. Add error handling and recovery
