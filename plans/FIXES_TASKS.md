# DevPocket Fixes Task Plan

## Overview
This document tracks the three fixes requested by the user.

## Tasks

### 1. Fix sudo support for devpocket user in default environment templates ✅ COMPLETED
**Status**: Completed
**Description**: The current default environment templates don't support `sudo` for the default user ("devpocket") to install packages in the container.

**Changes Made**:
- Updated `environment_service.py` to create "devpocket" user instead of "devuser"
- Added proper sudo setup in container creation command
- Updated all template configurations to include sudo support:
  - Python template: Already had sudo support ✓
  - Node.js template: Already had sudo support ✓
  - Golang template: Added full sudo support ✓
  - Rust template: Added full sudo support ✓
  - Ubuntu template: Already had sudo support ✓
- Created verification script `scripts/verify_sudo_in_templates.py` to ensure all templates have proper sudo support
- All templates now include:
  - sudo package installation
  - devpocket user creation
  - sudo group membership
  - NOPASSWD configuration in sudoers

### 2. Fix bottom tab bar icons to always show (not just when active) ❌ PENDING
**Status**: Pending - Client-side issue
**Description**: Items in the bottom tab bar don't show icons by default (the icon only shows up when the tab is active). Want all icons to show up by default, and change color when they're active.

**Notes**: This is a client-side mobile app issue and cannot be fixed in the server repository. The mobile app code is in a separate repository.

### 3. Enhance browser tab functionality ❌ PENDING
**Status**: Pending - Client-side issue
**Description**: The browser tab should be able to input any URL just like the native browser, with features like reload, open in external browser, and developer console logs.

**Notes**: This is a client-side mobile app issue and cannot be fixed in the server repository. The mobile app code is in a separate repository.

## Summary

- ✅ 1/3 tasks completed (sudo support)
- ❌ 2/3 tasks require client-side changes in the mobile app repository

The server-side fix for sudo support has been successfully implemented and verified. The remaining two issues (tab bar icons and browser functionality) need to be addressed in the mobile app codebase.
