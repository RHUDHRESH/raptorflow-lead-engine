-- Raptorflow Lead Engine Database Initialization
-- PostgreSQL schema setup for production

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create database if not exists (run as superuser)
SELECT 'CREATE DATABASE raptorflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'raptorflow');

-- Switch to raptorflow database
\c raptorflow;

-- Create tables (same structure as SQLite but with PostgreSQL optimizations)
CREATE TABLE IF NOT EXISTS icp_profiles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    size_buckets JSONB DEFAULT '[]',
    industries JSONB DEFAULT '[]',
    locations JSONB DEFAULT '[]',
    stages JSONB DEFAULT '[]',
    hiring_keywords JSONB DEFAULT '[]',
    pain_keywords JSONB DEFAULT '[]',
    channel_preferences JSONB DEFAULT '[]',
    budget_signals JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    website VARCHAR(255) UNIQUE,
    description TEXT,
    size_bucket VARCHAR(50),
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100) DEFAULT 'india',
    sector VARCHAR(100),
    marketing_stack_guess TEXT,
    is_marketing_pain_clear BOOLEAN DEFAULT FALSE,
    company_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contacts (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    name VARCHAR(255),
    role VARCHAR(100),
    email VARCHAR(255) UNIQUE,
    phone_numbers JSONB DEFAULT '[]',
    whatsapp_number VARCHAR(20),
    social_links JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS signals (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE SET NULL,
    lead_id INTEGER,
    source_type VARCHAR(50) NOT NULL,
    source_url VARCHAR(500),
    raw_text TEXT NOT NULL,
    signal_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leads (
    id SERIAL PRIMARY KEY,
    company_id INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    contact_id INTEGER REFERENCES contacts(id) ON DELETE SET NULL,
    score_icp_fit FLOAT DEFAULT 0,
    score_marketing_pain FLOAT DEFAULT 0,
    score_data_quality FLOAT DEFAULT 0,
    score_executive_level FLOAT DEFAULT 0,
    score_budget_potential FLOAT DEFAULT 0,
    total_score FLOAT DEFAULT 0,
    score_bucket VARCHAR(20) DEFAULT 'parked',
    icp_matches JSONB DEFAULT '[]',
    role_type VARCHAR(50),
    pain_tags JSONB DEFAULT '[]',
    situation TEXT,
    problem TEXT,
    implication TEXT,
    need_payoff TEXT,
    economic_buyer_guess VARCHAR(100),
    key_pain TEXT,
    chaos_flags JSONB DEFAULT '[]',
    silver_bullet_phrases JSONB DEFAULT '[]',
    context_dossier TEXT,
    challenger_insight TEXT,
    reframe_suggestion TEXT,
    hidden_motivations JSONB,
    competitive_threats JSONB,
    psychological_profile JSONB,
    attack_strategy JSONB,
    unique_intelligence JSONB,
    social_profiles JSONB,
    news_mentions JSONB,
    tech_stack JSONB,
    status VARCHAR(20) DEFAULT 'new',
    owner VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outreach_logs (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    outreach_type VARCHAR(50) NOT NULL,
    message_sent TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    response_received BOOLEAN DEFAULT FALSE,
    response_text TEXT
);

CREATE TABLE IF NOT EXISTS activities (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    type VARCHAR(20) NOT NULL,
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scrape_schedules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    schedule_type VARCHAR(20) DEFAULT 'interval',
    cron_expression VARCHAR(100),
    interval_minutes INTEGER,
    job_type VARCHAR(50) NOT NULL,
    job_params JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(name);
CREATE INDEX IF NOT EXISTS idx_companies_website ON companies(website);
CREATE INDEX IF NOT EXISTS idx_leads_total_score ON leads(total_score);
CREATE INDEX IF NOT EXISTS idx_leads_score_bucket ON leads(score_bucket);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_company_id ON leads(company_id);
CREATE INDEX IF NOT EXISTS idx_signals_company_id ON signals(company_id);
CREATE INDEX IF NOT EXISTS idx_signals_source_type ON signals(source_type);
CREATE INDEX IF NOT EXISTS idx_contacts_company_id ON contacts(company_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
CREATE INDEX IF NOT EXISTS idx_activities_lead_id ON activities(lead_id);
CREATE INDEX IF NOT EXISTS idx_outreach_logs_lead_id ON outreach_logs(lead_id);

-- Create GIN indexes for JSONB columns for faster querying
CREATE INDEX IF NOT EXISTS idx_icp_profiles_size_buckets ON icp_profiles USING GIN (size_buckets);
CREATE INDEX IF NOT EXISTS idx_icp_profiles_industries ON icp_profiles USING GIN (industries);
CREATE INDEX IF NOT EXISTS idx_leads_icp_matches ON leads USING GIN (icp_matches);
CREATE INDEX IF NOT EXISTS idx_leads_pain_tags ON leads USING GIN (pain_tags);

-- Create updated_at triggers
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_icp_profiles_updated_at BEFORE UPDATE ON icp_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_companies_updated_at BEFORE UPDATE ON companies FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON contacts FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_signals_updated_at BEFORE UPDATE ON signals FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_leads_updated_at BEFORE UPDATE ON leads FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_scrape_schedules_updated_at BEFORE UPDATE ON scrape_schedules FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default ICP profile
INSERT INTO icp_profiles (name, description, size_buckets, industries, pain_keywords, hiring_keywords)
VALUES (
    'Micro D2C Brands',
    'Small direct-to-consumer brands with marketing pain',
    '["1", "2-5", "6-10"]',
    '["d2c", "ecommerce", "consumer_goods"]',
    '["lead generation", "customer acquisition", "scaling ads", "conversion rate"]',
    '["marketing manager", "growth hacker", "digital marketer"]'
)
ON CONFLICT (name) DO NOTHING;

-- Create read-only user for monitoring
CREATE USER raptorflow_monitor WITH PASSWORD 'monitor_password';
GRANT CONNECT ON DATABASE raptorflow TO raptorflow_monitor;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO raptorflow_monitor;

