-- ============================================================
-- Kudi Ecosystem — Initial Database Schema
-- Supabase (PostgreSQL) Migration
-- ============================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================
-- ENUM TYPES
-- ============================================================

CREATE TYPE user_type_enum AS ENUM ('individual', 'freelancer', 'sme');
CREATE TYPE subscription_tier_enum AS ENUM ('free', 'pro', 'business');
CREATE TYPE transaction_type_enum AS ENUM ('income', 'expense');
CREATE TYPE income_category_enum AS ENUM (
  'salary', 'freelance', 'business', 'investment', 'rental',
  'capital_gains', 'forex_gains', 'crypto_gains', 'dividend', 'other'
);
CREATE TYPE expense_category_enum AS ENUM (
  'business_expense', 'personal', 'deductible', 'non_deductible',
  'rent', 'insurance', 'pension', 'nhf', 'nhis', 'other'
);
CREATE TYPE currency_enum AS ENUM ('NGN', 'USD', 'GBP', 'EUR', 'BTC', 'USDT', 'ETH');
CREATE TYPE tax_type_enum AS ENUM ('pit', 'cit', 'vat', 'wht', 'development_levy');
CREATE TYPE compliance_status_enum AS ENUM ('pending', 'completed', 'overdue', 'not_applicable');
CREATE TYPE message_role_enum AS ENUM ('user', 'assistant', 'system', 'tool');
CREATE TYPE payment_provider_enum AS ENUM ('paystack', 'stripe');
CREATE TYPE payment_status_enum AS ENUM ('pending', 'success', 'failed', 'refunded');

-- ============================================================
-- USERS
-- ============================================================

CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  supabase_id TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  full_name TEXT NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT true,
  user_type user_type_enum NOT NULL DEFAULT 'individual',
  subscription_tier subscription_tier_enum NOT NULL DEFAULT 'free',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_users_supabase_id ON users(supabase_id);
CREATE INDEX idx_users_email ON users(email);

-- ============================================================
-- USER PROFILES
-- ============================================================

CREATE TABLE user_profiles (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  tin TEXT,
  state_of_residence VARCHAR(100),
  employment_status VARCHAR(50),
  company_name VARCHAR(255),
  rc_number VARCHAR(50),
  company_size VARCHAR(20),
  annual_gross_income DOUBLE PRECISION,
  phone_number VARCHAR(20),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- TRANSACTIONS
-- ============================================================

CREATE TABLE transactions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  transaction_type transaction_type_enum NOT NULL,
  income_category income_category_enum,
  expense_category expense_category_enum,
  description TEXT NOT NULL,
  amount DOUBLE PRECISION NOT NULL,
  currency currency_enum NOT NULL DEFAULT 'NGN',
  amount_ngn DOUBLE PRECISION NOT NULL,
  exchange_rate DOUBLE PRECISION NOT NULL DEFAULT 1.0,
  transaction_date DATE NOT NULL,
  is_vat_applicable BOOLEAN NOT NULL DEFAULT false,
  is_wht_applicable BOOLEAN NOT NULL DEFAULT false,
  is_capital BOOLEAN NOT NULL DEFAULT false,
  source VARCHAR(50) NOT NULL DEFAULT 'manual',
  ai_classified BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_transactions_user_id ON transactions(user_id);
CREATE INDEX idx_transactions_type ON transactions(transaction_type);
CREATE INDEX idx_transactions_date ON transactions(transaction_date);
CREATE INDEX idx_transactions_user_date ON transactions(user_id, transaction_date);

-- ============================================================
-- TAX CALCULATIONS
-- ============================================================

CREATE TABLE tax_calculations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  tax_type tax_type_enum NOT NULL,
  year INTEGER NOT NULL,
  gross_income DOUBLE PRECISION NOT NULL,
  total_deductions DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  taxable_income DOUBLE PRECISION NOT NULL,
  tax_liability DOUBLE PRECISION NOT NULL,
  effective_rate DOUBLE PRECISION NOT NULL,
  breakdown JSONB NOT NULL DEFAULT '{}',
  is_scenario BOOLEAN NOT NULL DEFAULT false,
  scenario_label VARCHAR(255),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tax_calculations_user_id ON tax_calculations(user_id);
CREATE INDEX idx_tax_calculations_user_year ON tax_calculations(user_id, year);

-- ============================================================
-- TAX DEDUCTIONS
-- ============================================================

CREATE TABLE tax_deductions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  year INTEGER NOT NULL,
  deduction_type VARCHAR(50) NOT NULL,
  description TEXT NOT NULL,
  amount DOUBLE PRECISION NOT NULL,
  is_verified BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_tax_deductions_user_id ON tax_deductions(user_id);
CREATE INDEX idx_tax_deductions_user_year ON tax_deductions(user_id, year);

-- ============================================================
-- COMPLIANCE ITEMS
-- ============================================================

CREATE TABLE compliance_items (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  description TEXT NOT NULL,
  due_date DATE,
  status compliance_status_enum NOT NULL DEFAULT 'pending',
  tax_type tax_type_enum NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_compliance_items_user_id ON compliance_items(user_id);

-- ============================================================
-- CHAT CONVERSATIONS
-- ============================================================

CREATE TABLE chat_conversations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_chat_conversations_user_id ON chat_conversations(user_id);

-- ============================================================
-- CHAT MESSAGES
-- ============================================================

CREATE TABLE chat_messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  conversation_id UUID NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
  role message_role_enum NOT NULL,
  content TEXT NOT NULL,
  tool_calls JSONB,
  tool_results JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_chat_messages_conversation_id ON chat_messages(conversation_id);
CREATE INDEX idx_chat_messages_created_at ON chat_messages(conversation_id, created_at);

-- ============================================================
-- SUBSCRIPTIONS
-- ============================================================

CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
  provider payment_provider_enum NOT NULL,
  provider_subscription_id VARCHAR(255),
  provider_customer_id VARCHAR(255),
  plan_code VARCHAR(50) NOT NULL,
  is_active BOOLEAN NOT NULL DEFAULT true,
  current_period_end TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- PAYMENT HISTORY
-- ============================================================

CREATE TABLE payment_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  provider payment_provider_enum NOT NULL,
  provider_reference VARCHAR(255) NOT NULL,
  amount DOUBLE PRECISION NOT NULL,
  currency VARCHAR(10) NOT NULL,
  status payment_status_enum NOT NULL,
  description VARCHAR(255),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_payment_history_user_id ON payment_history(user_id);

-- ============================================================
-- RAG DOCUMENT EMBEDDINGS (pgvector)
-- ============================================================

CREATE TABLE document_embeddings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  document_name TEXT NOT NULL,
  chunk_index INTEGER NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}',
  embedding vector(384),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_document_embeddings_name ON document_embeddings(document_name);
CREATE INDEX idx_document_embeddings_vector ON document_embeddings
  USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================
-- ROW LEVEL SECURITY (RLS)
-- ============================================================

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax_calculations ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax_deductions ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_history ENABLE ROW LEVEL SECURITY;

-- Users can only read/write their own data
CREATE POLICY "Users can view own record" ON users
  FOR SELECT USING (supabase_id = auth.uid()::text);

CREATE POLICY "Users can update own record" ON users
  FOR UPDATE USING (supabase_id = auth.uid()::text);

CREATE POLICY "Users can view own profile" ON user_profiles
  FOR SELECT USING (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

CREATE POLICY "Users can update own profile" ON user_profiles
  FOR UPDATE USING (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

CREATE POLICY "Users can insert own profile" ON user_profiles
  FOR INSERT WITH CHECK (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

-- Transactions
CREATE POLICY "Users can view own transactions" ON transactions
  FOR SELECT USING (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

CREATE POLICY "Users can insert own transactions" ON transactions
  FOR INSERT WITH CHECK (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

CREATE POLICY "Users can update own transactions" ON transactions
  FOR UPDATE USING (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

CREATE POLICY "Users can delete own transactions" ON transactions
  FOR DELETE USING (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

-- Tax calculations
CREATE POLICY "Users can view own tax calculations" ON tax_calculations
  FOR SELECT USING (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

CREATE POLICY "Users can insert own tax calculations" ON tax_calculations
  FOR INSERT WITH CHECK (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

-- Tax deductions
CREATE POLICY "Users can view own deductions" ON tax_deductions
  FOR SELECT USING (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

CREATE POLICY "Users can insert own deductions" ON tax_deductions
  FOR INSERT WITH CHECK (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

CREATE POLICY "Users can update own deductions" ON tax_deductions
  FOR UPDATE USING (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

-- Compliance items
CREATE POLICY "Users can view own compliance items" ON compliance_items
  FOR SELECT USING (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

CREATE POLICY "Users can insert own compliance items" ON compliance_items
  FOR INSERT WITH CHECK (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

-- Chat conversations
CREATE POLICY "Users can view own conversations" ON chat_conversations
  FOR SELECT USING (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

CREATE POLICY "Users can insert own conversations" ON chat_conversations
  FOR INSERT WITH CHECK (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

CREATE POLICY "Users can delete own conversations" ON chat_conversations
  FOR DELETE USING (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

-- Chat messages (via conversation ownership)
CREATE POLICY "Users can view own messages" ON chat_messages
  FOR SELECT USING (conversation_id IN (
    SELECT id FROM chat_conversations WHERE user_id IN (
      SELECT id FROM users WHERE supabase_id = auth.uid()::text
    )
  ));

CREATE POLICY "Users can insert own messages" ON chat_messages
  FOR INSERT WITH CHECK (conversation_id IN (
    SELECT id FROM chat_conversations WHERE user_id IN (
      SELECT id FROM users WHERE supabase_id = auth.uid()::text
    )
  ));

-- Subscriptions
CREATE POLICY "Users can view own subscription" ON subscriptions
  FOR SELECT USING (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

-- Payment history
CREATE POLICY "Users can view own payments" ON payment_history
  FOR SELECT USING (user_id IN (SELECT id FROM users WHERE supabase_id = auth.uid()::text));

-- Document embeddings are readable by all authenticated users (public knowledge base)
ALTER TABLE document_embeddings ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Authenticated users can read embeddings" ON document_embeddings
  FOR SELECT USING (auth.role() = 'authenticated');

-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Auto-create user record when Supabase auth user signs up
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
DECLARE
  new_user_id UUID;
  meta_user_type TEXT;
BEGIN
  meta_user_type := COALESCE(NEW.raw_user_meta_data->>'user_type', 'individual');

  IF meta_user_type NOT IN ('individual', 'freelancer', 'sme') THEN
    meta_user_type := 'individual';
  END IF;

  INSERT INTO public.users (supabase_id, email, full_name, user_type)
  VALUES (
    NEW.id::text,
    COALESCE(NEW.email, ''),
    COALESCE(NEW.raw_user_meta_data->>'full_name', 'User'),
    meta_user_type::public.user_type_enum
  )
  RETURNING id INTO new_user_id;

  INSERT INTO public.user_profiles (user_id)
  VALUES (new_user_id);

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- Trigger on Supabase auth.users insert
CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at trigger to all tables
CREATE TRIGGER set_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON user_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON transactions FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON tax_calculations FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON tax_deductions FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON compliance_items FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON chat_conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON chat_messages FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON subscriptions FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER set_updated_at BEFORE UPDATE ON payment_history FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- VECTOR SIMILARITY SEARCH FUNCTION
-- ============================================================

CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(384),
  match_threshold FLOAT DEFAULT 0.7,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  document_name TEXT,
  chunk_index INTEGER,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    de.id,
    de.document_name,
    de.chunk_index,
    de.content,
    de.metadata,
    1 - (de.embedding <=> query_embedding) AS similarity
  FROM document_embeddings de
  WHERE 1 - (de.embedding <=> query_embedding) > match_threshold
  ORDER BY de.embedding <=> query_embedding
  LIMIT match_count;
END;
$$;
