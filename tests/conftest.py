"""Use a disposable runtime before application modules read their paths."""
import atexit
import os
import shutil
import tempfile
from pathlib import Path

TEST_RUNTIME = Path(tempfile.mkdtemp(prefix="ai-course-studio-tests-"))
os.environ["AI_COURSE_STUDIO_RUNTIME_DIR"] = str(TEST_RUNTIME)
os.environ["APP_ENV"] = "test"
os.environ["PUBLIC_ACCESS"] = "false"

def pytest_configure(config):
    # Keep pytest's fixtures away from shared Windows temp directories with stale ACLs.
    if not config.option.basetemp:
        config.option.basetemp = str(TEST_RUNTIME / 'pytest')

@atexit.register
def _remove_test_runtime() -> None:
    shutil.rmtree(TEST_RUNTIME, ignore_errors=True)
