"""
Migration script to add referral system columns to existing database
Run this once: python migrate_referral.py
"""
import asyncio
from sqlalchemy import text
from database.db import engine

async def migrate():
    async with engine.begin() as conn:
        print("🔄 Starting migration...")
        
        # Add referral_code column
        try:
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS referral_code VARCHAR(20) UNIQUE;
            """))
            print("✅ Added referral_code column")
        except Exception as e:
            print(f"⚠️ referral_code: {e}")
        
        # Add referred_by column
        try:
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS referred_by BIGINT REFERENCES users(telegram_id);
            """))
            print("✅ Added referred_by column")
        except Exception as e:
            print(f"⚠️ referred_by: {e}")
        
        # Add balance column
        try:
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS balance FLOAT DEFAULT 0.0;
            """))
            print("✅ Added balance column")
        except Exception as e:
            print(f"⚠️ balance: {e}")
        
        # Add total_earned column
        try:
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS total_earned FLOAT DEFAULT 0.0;
            """))
            print("✅ Added total_earned column")
        except Exception as e:
            print(f"⚠️ total_earned: {e}")
        
        # Add created_at column to users
        try:
            await conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
            """))
            print("✅ Added created_at column to users")
        except Exception as e:
            print(f"⚠️ created_at: {e}")
        
        # Create index on referral_code
        try:
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_referral_code 
                ON users(referral_code);
            """))
            print("✅ Created index on referral_code")
        except Exception as e:
            print(f"⚠️ index referral_code: {e}")
        
        # Add referral_reward to settings
        try:
            await conn.execute(text("""
                ALTER TABLE settings 
                ADD COLUMN IF NOT EXISTS referral_reward FLOAT DEFAULT 1000.0;
            """))
            print("✅ Added referral_reward to settings")
        except Exception as e:
            print(f"⚠️ referral_reward: {e}")
        
        # Create referral_history table
        try:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS referral_history (
                    id SERIAL PRIMARY KEY,
                    referrer_id BIGINT NOT NULL REFERENCES users(telegram_id),
                    referred_id BIGINT NOT NULL REFERENCES users(telegram_id),
                    reward_amount FLOAT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """))
            print("✅ Created referral_history table")
        except Exception as e:
            print(f"⚠️ referral_history: {e}")
        
        # Create indexes on referral_history
        try:
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_referral_history_referrer 
                ON referral_history(referrer_id);
            """))
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_referral_history_referred 
                ON referral_history(referred_id);
            """))
            print("✅ Created indexes on referral_history")
        except Exception as e:
            print(f"⚠️ indexes: {e}")
        
        print("\n✅ Migration completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate())
