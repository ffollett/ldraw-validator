from pathlib import Path
import sys

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

print("Importing validator.grounding...")
try:
    import validator.grounding
    print("validator.grounding imported.")
    print(f"Dir: {dir(validator.grounding)}")
    from validator.grounding import validate_grounding
    print("validate_grounding imported.")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Error: {e}")
