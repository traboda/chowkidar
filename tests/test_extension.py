"""
Tests for chowkidar/extension.py

Covers:
  - JWTAuthExtension.__init__ initializes all state variables
  - JWTAuthExtension can be instantiated without execution_context (new strawberry pattern)
  - resolve() doesn't crash with AttributeError
  - on_operation() generator hook works correctly
  - _init_request_state() resets state correctly
"""

from unittest.mock import MagicMock

import pytest
from strawberry.types import ExecutionContext


class TestExtensionInit:
    """Tests for JWTAuthExtension.__init__ state initialization."""

    def _make_extension(self, with_execution_context=True):
        """Create a JWTAuthExtension, optionally with a mocked execution context."""
        from chowkidar.extension import JWTAuthExtension

        if with_execution_context:
            mock_execution_context = MagicMock(spec=ExecutionContext)
            mock_execution_context.context = {"request": MagicMock()}
            ext = JWTAuthExtension(execution_context=mock_execution_context)
        else:
            ext = JWTAuthExtension()
        return ext

    def test_init_sets_request(self):
        ext = self._make_extension()
        assert ext._request is None

    def test_init_sets_userID(self):
        ext = self._make_extension()
        assert ext.userID is None

    def test_init_sets_refreshToken(self):
        ext = self._make_extension()
        assert ext.refreshToken is None

    def test_init_sets_refreshTokenObj(self):
        ext = self._make_extension()
        assert ext.refreshTokenObj is None

    def test_init_sets_new_JWT_access_token(self):
        ext = self._make_extension()
        assert ext._new_JWT_access_token is None

    def test_init_sets_remove_auth_cookies(self):
        ext = self._make_extension()
        assert ext._remove_auth_cookies is False

    def test_all_six_state_vars_exist_after_init(self):
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

    def test_init_without_execution_context(self):
        """Extension can be instantiated without execution_context (strawberry sets it later)."""
        ext = self._make_extension(with_execution_context=False)
        assert ext._request is None
        assert ext.userID is None

    def test_init_with_execution_context_backward_compat(self):
        """Passing execution_context explicitly still works (backward compatibility)."""
        from chowkidar.extension import JWTAuthExtension

        mock_ec = MagicMock(spec=ExecutionContext)
        mock_ec.context = {"request": MagicMock()}
        # Should not raise
        JWTAuthExtension(execution_context=mock_ec)


class TestResolveDefensiveGuards:
    """Tests that resolve() doesn't crash even in edge cases."""

    def _make_extension(self):
        from chowkidar.extension import JWTAuthExtension

        mock_execution_context = MagicMock(spec=ExecutionContext)
        mock_execution_context.context = {"request": MagicMock()}
        ext = JWTAuthExtension(execution_context=mock_execution_context)
        return ext

    def test_resolve_without_on_operation(self):
        """resolve() should NOT crash even if on_operation() was never called."""
        ext = self._make_extension()

        mock_info = MagicMock()
        mock_info.context = MagicMock()
        mock_info.context.request = MagicMock()

        mock_next = MagicMock(return_value="resolved_value")
        mock_root = MagicMock()

        result = ext.resolve(mock_next, mock_root, mock_info)
        assert result == "resolved_value"
        mock_next.assert_called_once()

    def test_resolve_after_deleting_state(self):
        """resolve() should handle missing attributes via hasattr/getattr guards."""
        ext = self._make_extension()

        if hasattr(ext, "_new_JWT_access_token"):
            del ext._new_JWT_access_token
        if hasattr(ext, "_remove_auth_cookies"):
            del ext._remove_auth_cookies

        mock_info = MagicMock()
        mock_info.context = MagicMock()
        mock_info.context.request = MagicMock()
        mock_next = MagicMock(return_value="ok")
        mock_root = MagicMock()

        result = ext.resolve(mock_next, mock_root, mock_info)
        assert result == "ok"

    def test_resolve_sets_context_attributes(self):
        """resolve() should set userID, refreshToken, etc. on info.context."""
        ext = self._make_extension()
        ext.userID = 42
        ext.refreshToken = "test-token"
        ext._request = "mock-request"

        class SimpleContext:
            pass

        ctx = SimpleContext()

        mock_info = MagicMock()
        mock_info.context = ctx
        mock_next = MagicMock(return_value="ok")
        mock_root = MagicMock()

        ext.resolve(mock_next, mock_root, mock_info)

        assert ctx.userID == 42
        assert ctx.refreshToken == "test-token"
        assert ctx.refreshTokenObj is None
        assert ctx.request == "mock-request"


class TestOnOperation:
    """Tests for the on_operation() generator hook."""

    def _make_extension(self):
        from chowkidar.extension import JWTAuthExtension

        mock_execution_context = MagicMock(spec=ExecutionContext)
        mock_request = MagicMock()
        mock_request.COOKIES = {}
        mock_execution_context.context = {"request": mock_request}
        ext = JWTAuthExtension()
        # Strawberry sets execution_context on the instance before calling hooks
        ext.execution_context = mock_execution_context
        return ext

    def test_on_operation_is_generator(self):
        """on_operation() should be a generator that yields once."""
        ext = self._make_extension()
        gen = ext.on_operation()
        next(gen)
        with pytest.raises(StopIteration):
            next(gen)

    def test_on_operation_sets_request(self):
        """on_operation() should set _request from execution context."""
        ext = self._make_extension()
        gen = ext.on_operation()
        next(gen)
        assert ext._request is not None


class TestInitRequestState:
    """Tests for _init_request_state() reset behavior."""

    def _make_extension(self):
        from chowkidar.extension import JWTAuthExtension

        mock_execution_context = MagicMock(spec=ExecutionContext)
        mock_execution_context.context = {"request": MagicMock()}
        return JWTAuthExtension(execution_context=mock_execution_context)

    def test_reset_clears_state(self):
        ext = self._make_extension()

        ext.userID = 99
        ext.refreshToken = "old-token"
        ext._new_JWT_access_token = {"token": "abc"}
        ext._remove_auth_cookies = True

        ext._init_request_state()

        assert ext._request is None
        assert ext.userID is None
        assert ext.refreshToken is None
        assert ext.refreshTokenObj is None
        assert ext._new_JWT_access_token is None
        assert ext._remove_auth_cookies is False

    def test_no_state_leakage_between_resets(self):
        ext = self._make_extension()

        ext.userID = 1
        ext._init_request_state()
        ext.userID = 2
        ext._init_request_state()

        assert ext.userID is None
