"""Use only this pinned action generation's metadata writer."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'private_dot_config/dotfiles-ai'))
from integration_coordinator.candidate_receipt import main

if __name__ == '__main__':
    raise SystemExit(main())
