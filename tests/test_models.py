"""
Tests for chowkidar/models.py

Covers:
  - AbstractRefreshToken uses UniqueConstraint (not unique_together)
  - The constraint name uses %(app_label)s_%(class)s_ template
"""
from django.db import models

from chowkidar.models import AbstractRefreshToken


class TestAbstractRefreshTokenMeta:
    """Tests for the Meta class migration from unique_together to UniqueConstraint."""

    def test_no_unique_together(self):
        """unique_together should NOT be set (removed for Django 6 compat)."""
        meta = AbstractRefreshToken._meta
        assert not meta.unique_together, (
            f"unique_together should be empty, got: {meta.unique_together}"
        )

    def test_has_constraints(self):
        """Meta.constraints should have at least one UniqueConstraint."""
        constraints = AbstractRefreshToken._meta.constraints
        assert len(constraints) >= 1, "Expected at least one constraint"

    def test_constraint_is_unique_constraint(self):
        """The constraint should be a UniqueConstraint instance."""
        constraint = AbstractRefreshToken._meta.constraints[0]
        assert isinstance(constraint, models.UniqueConstraint)

    def test_constraint_fields(self):
        """The constraint should cover (token, revoked) fields."""
        constraint = AbstractRefreshToken._meta.constraints[0]
        assert list(constraint.fields) == ["token", "revoked"]

    def test_constraint_name_uses_template(self):
        """The constraint name should use %(app_label)s_%(class)s_ template
        for abstract model compatibility."""
        constraint = AbstractRefreshToken._meta.constraints[0]
        # The raw name before resolution should contain the template
        assert "%(app_label)s" in constraint.name or "%(class)s" in constraint.name, (
            f"Constraint name should use template syntax, got: {constraint.name}"
        )
