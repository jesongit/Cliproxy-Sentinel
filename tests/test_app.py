from pathlib import Path

from cliproxyapi.app import _default_config_path


def test_default_config_path_points_to_root_config_yaml() -> None:
    expected = Path(__file__).resolve().parents[1] / "config.yaml"
    assert _default_config_path() == expected
