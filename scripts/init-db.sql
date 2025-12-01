-- RecycleOps AI Assistant - Database Initialization Script
-- This script runs automatically when PostgreSQL container starts for the first time

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom types
DO $$ BEGIN
    CREATE TYPE severity_level AS ENUM ('critical', 'high', 'medium', 'low', 'info');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- Grant necessary privileges
GRANT ALL PRIVILEGES ON DATABASE recycleops TO recycleops;
