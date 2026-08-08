"""Add project root to sys.path so `src.*` and `config.*` imports resolve from tests/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def pytest_configure(config):
    # pandas_ta sets mode.copy_on_write on import — deprecated in pandas 3+.
    # Can't fix a third-party library; suppress it so test output stays clean.
    config.addinivalue_line("filterwarnings", "ignore::DeprecationWarning:pandas_ta")
    config.addinivalue_line("filterwarnings", "ignore:.*copy_on_write.*:DeprecationWarning")
