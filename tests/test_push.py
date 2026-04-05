"""Tests for git push operations."""

import pytest
from unittest.mock import patch, MagicMock
from folio.push import push_profile


class TestPushProfile:

    @patch("folio.push.Repo")
    def test_stages_correct_files(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        push_profile("/fake/repo")
        added_files = mock_repo.index.add.call_args[0][0]
        assert "README.md" in added_files
        assert "dist" in added_files

    @patch("folio.push.Repo")
    def test_commit_message_format(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        push_profile("/fake/repo")
        commit_msg = mock_repo.index.commit.call_args[0][0]
        assert commit_msg.startswith("folio: regenerate profile")

    @patch("folio.push.Repo")
    def test_pushes_to_origin(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        push_profile("/fake/repo")
        mock_repo.remotes.origin.push.assert_called_once()

    @patch("folio.push.Repo")
    def test_no_force_push(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        push_profile("/fake/repo")
        args, kwargs = mock_repo.remotes.origin.push.call_args
        assert kwargs.get("force", False) is False
