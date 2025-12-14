#!/usr/bin/env python3

print("Testing Raptorflow database schema changes...")

try:
    from database import engine, Lead, ICPProfile, Company
    print("OK: Database models imported successfully")

    # Check if Lead model has new columns
    required_columns = [
        'score_executive_level', 'score_budget_potential',
        'hidden_motivations', 'competitive_threats', 'psychological_profile',
        'attack_strategy', 'unique_intelligence', 'social_profiles',
        'news_mentions', 'tech_stack'
    ]

    lead_columns = Lead.__table__.columns.keys()
    print(f"Lead model has {len(lead_columns)} columns")

    missing = []
    for col in required_columns:
        if col not in lead_columns:
            missing.append(col)

    if missing:
        print(f"ERROR: MISSING COLUMNS: {missing}")
    else:
        print("OK: All enhanced Lead columns present")

    print("Schema verification complete!")

except Exception as e:
    print(f"DATABASE ERROR: {e}")
    import traceback
    traceback.print_exc()
