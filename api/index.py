import os
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from src.main import app
