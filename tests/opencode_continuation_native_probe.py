"""Run the managed probe from the source checkout without duplicating it."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).parents[1] / "dot_local/share/opencode-continuation/native_probe.py"),
                  run_name="__main__")
