import sys
import os
sys.path.append(os.path.join(os.getcwd(), "backend"))

try:
    from database import Base, Signal
    print("Successfully imported Signal")
    print(Signal.__table__.columns.keys())
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
