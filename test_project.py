""" Testing all project steps. """
import pytest
from pathlib import Path
import sys
from spacy.cli.project.run import project_run
from spacy.cli.project.assets import project_assets


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Skipping on Windows (for now) due to platform-specific scripts.",
)
def test_wikid():
    root = Path(__file__).parent
    project_assets(root)
    project_run(root, "parse", capture=True)
    # project_run(root, "download_model", capture=True)
    project_run(root, "create_kb", capture=True)
