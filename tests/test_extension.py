"""
Tests for chowkidar/extension.py

Covers:
  - JWTAuthExtension.__init__ initializes all state variables
  - resolve() doesn't crash with AttributeError (the critical bug fix)
  - _init_request_state() resets state correctly
"""
from unittest.mock import MagicMock, patch
from datetime import timedelta

import pytest

from strawberry.types import ExecutionContext


class TestExtensionInit:
    """Tests for JWTAuthExtension.__init__ state initialization."""

    def _make_extension(self):
        """Create a JWTAuthExtension with a mocked execution context."""
        from chowkidar.extension import JWTAuthExtension

        mock_execution_context = MagicMock(spec=ExecutionContext)
        mock_execution_context.context = {"request": MagicMock()}
        ext = JWTAuthExtension(execution_context=mock_execution_context)
        return ext

    def test_init_sets_request(self):
        """__init__ should set _request to None."""
        ext = self._make_extension()
        assert ext._request is None

    def test_init_sets_userID(self):
        """__init__ should set userID to None."""
        ext = self._make_extension()
        assert ext.userID is None

    def test_init_sets_refreshToken(self):
        """__init__ should set refreshToken to None."""
        ext = self._make_extension()
        assert ext.refreshToken is None

    def test_init_sets_refreshTokenObj(self):
        """__init__ should set refreshTokenObj to None."""
        ext = self._make_extension()
        assert ext.refreshTokenObj is None

    def test_init_sets_new_JWT_access_token(self):
        """__init__ should set _new_JWT_access_token to None.
        This is the attribute that caused the original AttributeError.
        """
        ext = self._make_extension()
        assert ext._new_JWT_access_token is None

    def test_init_sets_remove_auth_cookies(self):
        """__init__ should set _remove_auth_cookies to False."""
        ext = self._make_extension()
        assert ext._remove_auth_cookies is False

    def test_all_six_state_vars_exist_after_init(self):
        """All 6 state variables should exist immediately after __init__.
        This is the core test for the critical bug fix.
        """
        ext = self._make_extension()
        attrs = [
            "_request",
            "userID",
            "refreshToken",
            "refreshTokenObj",
            "_new_JWT_access_token",
            "_remove_auth_cookies",
        ]
        for attr in attrs:
            assert hasattr(ext, attr), f"Missing attribute after __init__: {attr}"


class TestResolveDefensiveGuards:
    """Tests that resolve() doesn't crash even in edge cases."""

    def _make_extension(self):
        from chowkidar.extension import JWTAuthExtension

        mock_execution_context = MagicMock(spec=ExecutionContext)
        mock_execution_context.context = {"request": MagicMock()}
        ext = JWTAuthExtension(execution_context=mock_execution_context)
        return ext

    def test_resolve_without_on_request_start(self):
        """resolve() should NOT crash even if on_request_start() was never called.
        This simulates the exact bug from the error report.
        """
        ext = self._make_extension()

        # Create mock info object
        mock_info = MagicMock()
        mock_info.context = MagicMock()
        mock_info.context.request = MagicMock()

        mock_next = MagicMock(return_value="resolved_value")
        mock_root = MagicMock()

        # This should NOT raise AttributeError
        result = ext.resolve(mock_next, mock_root, mock_info)
        assert result == "resolved_value"
        mock_next.assert_called_once()

    def test_resolve_after_deleting_state(self):
        """resolve() should handle missing attributes via hasattr/getattr guards."""
        ext = self._make_extension()

        # Forcefully delete state to simulate extreme edge case
        if hasattr(ext, "_new_JWT_access_token"):
            del ext._new_JWT_access_token
        if hasattr(ext, "_remove_auth_cookies"):
            del ext._remove_auth_cookies

        mock_info = MagicMock()
        mock_info.context = MagicMock()
        mock_info.context.request = MagicMock()
        mock_next = MagicMock(return_value="ok")
        mock_root = MagicMock()

        # Should still not crash — defensive hasattr guards catch this
        result = ext.resolve(mock_next, mock_root, mock_info)
        assert result == "ok"

    def test_resolve_sets_context_attributes(self):
        """resolve() should set userID, refreshToken, etc. on info.context."""
        ext = self._make_extension()
        ext.userID = 42
        ext.refreshToken = "test-token"
        ext._request = "mock-request"

        # Use a simple namespace object instead of MagicMock for context
        # so that setattr calls actually stick
        class SimpleContext:
            pass

        ctx = SimpleContext()

        mock_info = MagicMock()
        mock_info.context = ctx
        mock_next = MagicMock(return_value="ok")
        mock_root = MagicMock()

        ext.resolve(mock_next, mock_root, mock_info)

        # Verify context was populated by resolve()
        assert ctx.userID == 42
        assert ctx.refreshToken == "test-token"
        assert ctx.refreshTokenObj is None
        assert ctx.request == "mock-request"


class TestInitRequestState:
    """Tests for _init_request_state() reset behavior."""

    def _make_extension(self):
        from chowkidar.extension import JWTAuthExtension

        mock_execution_context = MagicMock(spec=ExecutionContext)
        mock_execution_context.context = {"request": MagicMock()}
        return JWTAuthExtension(execution_context=mock_execution_context)

    def test_reset_clears_state(self):
        """_init_request_state() should reset all state to defaults."""
        ext = self._make_extension()

        # Set state as if a request was processed
        ext.userID = 99
        ext.refreshToken = "old-token"
        ext._new_JWT_access_token = {"token": "abc"}
        ext._remove_auth_cookies = True

        # Reset
        ext._init_request_state()

        # All should be back to defaults
        assert ext._request is None
        assert ext.userID is None
        assert ext.refreshToken is None
        assert ext.refreshTokenObj is None
        assert ext._new_JWT_access_token is None
        assert ext._remove_auth_cookies is False

    def test_no_state_leakage_between_resets(self):
        """Calling _init_request_state() twice should produce clean state."""
        ext = self._make_extension()

        ext.userID = 1
        ext._init_request_state()
        ext.userID = 2
        ext._init_request_state()

        assert ext.userID is None
