import os
import sys

# Add repository root to python path so top-level modules like `extensions` and `hooks` can be imported in tests
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
