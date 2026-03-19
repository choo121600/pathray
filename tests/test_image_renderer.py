"""Tests for image_renderer module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from pathray.erd.image_renderer import render_images


@pytest.fixture
def mmd_file(tmp_path) -> Path:
    f = tmp_path / "erd.mmd"
    f.write_text("erDiagram\n    User {\n        integer id PK\n    }\n")
    return f


def _make_completed_process(returncode=0, stdout="", stderr=""):
    result = MagicMock(spec=subprocess.CompletedProcess)
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class TestRenderImagesSuccess:
    def test_returns_png_and_svg_paths(self, mmd_file):
        with patch("subprocess.run", return_value=_make_completed_process()):
            result = render_images(mmd_file)
        assert result["png"] is not None
        assert result["svg"] is not None

    def test_png_path_has_correct_extension(self, mmd_file):
        with patch("subprocess.run", return_value=_make_completed_process()):
            result = render_images(mmd_file)
        assert result["png"].suffix == ".png"

    def test_svg_path_has_correct_extension(self, mmd_file):
        with patch("subprocess.run", return_value=_make_completed_process()):
            result = render_images(mmd_file)
        assert result["svg"].suffix == ".svg"

    def test_output_in_same_dir_by_default(self, mmd_file):
        with patch("subprocess.run", return_value=_make_completed_process()):
            result = render_images(mmd_file)
        assert result["png"].parent == mmd_file.parent
        assert result["svg"].parent == mmd_file.parent

    def test_custom_output_dir(self, mmd_file, tmp_path):
        out_dir = tmp_path / "images"
        with patch("subprocess.run", return_value=_make_completed_process()):
            result = render_images(mmd_file, output_dir=out_dir)
        assert result["png"].parent == out_dir
        assert result["svg"].parent == out_dir

    def test_custom_output_dir_is_created(self, mmd_file, tmp_path):
        out_dir = tmp_path / "nested" / "output"
        with patch("subprocess.run", return_value=_make_completed_process()):
            render_images(mmd_file, output_dir=out_dir)
        assert out_dir.exists()

    def test_subprocess_called_with_npx(self, mmd_file):
        with patch("subprocess.run", return_value=_make_completed_process()) as mock_run:
            render_images(mmd_file)
        calls = mock_run.call_args_list
        assert len(calls) == 2
        for call in calls:
            args = call[0][0]
            assert args[0] == "npx"
            assert "@mermaid-js/mermaid-cli" in args

    def test_stem_used_for_output_filename(self, tmp_path):
        mmd = tmp_path / "my_diagram.mmd"
        mmd.write_text("erDiagram\n")
        with patch("subprocess.run", return_value=_make_completed_process()):
            result = render_images(mmd)
        assert result["png"].name == "my_diagram.png"
        assert result["svg"].name == "my_diagram.svg"


class TestRenderImagesNodeMissing:
    def test_returns_none_when_npx_not_found(self, mmd_file):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = render_images(mmd_file)
        assert result["png"] is None
        assert result["svg"] is None

    def test_logs_warning_when_npx_not_found(self, mmd_file, caplog):
        import logging
        with caplog.at_level(logging.WARNING, logger="pathray.erd.image_renderer"):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                render_images(mmd_file)
        assert "npx not found" in caplog.text

    def test_no_exception_raised_when_npx_missing(self, mmd_file):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = render_images(mmd_file)
        assert isinstance(result, dict)


class TestRenderImagesCalledProcessError:
    def test_returns_none_on_mmdc_failure(self, mmd_file):
        err = subprocess.CalledProcessError(1, "npx", stderr="error")
        with patch("subprocess.run", side_effect=err):
            result = render_images(mmd_file)
        assert result["png"] is None
        assert result["svg"] is None

    def test_logs_warning_on_mmdc_failure(self, mmd_file, caplog):
        import logging
        err = subprocess.CalledProcessError(1, "npx", stderr="some error")
        with caplog.at_level(logging.WARNING, logger="pathray.erd.image_renderer"):
            with patch("subprocess.run", side_effect=err):
                render_images(mmd_file)
        assert "mermaid-cli failed" in caplog.text
