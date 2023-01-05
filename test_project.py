""" Testing all project steps. """
from pathlib import Path
from spacy.cli.project.run import project_run
from spacy.cli.project.assets import project_assets


def test_project():
    vectors_model = "en_core_web_sm"
    root = Path(__file__).parent
    project_assets(root)
    project_run(
        root,
        "download_model",
        capture=True,
        overrides={"vars.vectors_model": vectors_model},
    )
    project_run(root, "parse", capture=True)
    project_run(
        root,
        "create_kb",
        capture=True,
        overrides={"vars.vectors_model": vectors_model},
    )
