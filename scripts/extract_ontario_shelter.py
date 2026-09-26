"""Extract and ingest one verified official background series."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from housing.background_series import extractor_main

if __name__ == "__main__":
    extractor_main('ontario_shelter')
