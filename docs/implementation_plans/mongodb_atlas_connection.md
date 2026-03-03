# Implementation Plan - MongoDB Atlas Connection

The goal is to update the application to connect to MongoDB Atlas instead of the local MongoDB instance.

## User Review Required

> [!IMPORTANT]
> **Database Password**: The connection string provided contains `<db_password>`. You will need to replace this with your actual MongoDB database password in the `.env` file I will create.

## Proposed Changes

### Configuration

#### [NEW] [backend/.env](file:///Users/xalandames/Documents/SwampHacks 2026/restailor/backend/.env)
- Create a new `.env` file to store sensitive configuration.
- Add `MONGODB_URI` with the Atlas connection string.

#### [MODIFY] [backend/app/config.py](file:///Users/xalandames/Documents/SwampHacks 2026/restailor/backend/app/config.py)
- The `Settings` class is already configured to read from `.env`.
- We can leave the default as localhost (fallback) or update it. I recommend leaving the default for local development if `.env` is missing, but since you explicitly want to switch, I will ensure the application prefers the environment variable.
- *(Optional)* I can comment out the local default to ensure it fails if the env var isn't set, avoiding accidental local writes.

## Verification Plan

### Manual Verification
1.  **Check Connection**:
    - Ran the backend server.
    - Verify it connects to Atlas (logs usually indicate connection success/failure).
    - Since I don't have the password, I will rely on you to verify the final connection after entering the password.
