"""RFC 7807 Problem Details models."""

from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class ProblemDetail:
    """RFC 7807 Problem Details object.

    See: https://datatracker.ietf.org/doc/html/rfc7807
    """

    type: str | None = None  # URI reference identifying the problem type
    title: str | None = None  # Short, human-readable summary
    status: int | None = None  # HTTP status code
    detail: str | None = None  # Human-readable explanation
    instance: str | None = None  # URI reference identifying specific occurrence

    # Extension members (additional fields from API)
    extensions: dict[str, Any] | None = None

    @classmethod
    def from_response(cls, response: httpx.Response) -> "ProblemDetail | None":
        """Parse RFC 7807 problem details from HTTP response.

        Args:
            response: HTTP response object

        Returns:
            ProblemDetail object or None if not RFC 7807 format
        """
        # Check if response has RFC 7807 content type
        content_type = response.headers.get("content-type", "")
        if "application/problem+json" not in content_type:
            # Try to parse as JSON anyway if it has the right structure
            try:
                data = response.json()
            except (ValueError, TypeError, AttributeError):
                # JSON decode errors, type errors, or missing .json() method
                return None

            # Check if it looks like RFC 7807 (has at least one standard field)
            standard_fields = {"type", "title", "status", "detail", "instance"}
            if not any(field in data for field in standard_fields):
                return None
        else:
            try:
                data = response.json()
            except (ValueError, TypeError, AttributeError):
                # JSON decode errors, type errors, or missing .json() method
                return None

        # Extract standard fields
        type_val = data.get("type")
        title = data.get("title")
        status = data.get("status")
        detail = data.get("detail")
        instance = data.get("instance")

        # Extract extension members (non-standard fields)
        standard_fields = {"type", "title", "status", "detail", "instance"}
        extensions = {k: v for k, v in data.items() if k not in standard_fields}

        return cls(
            type=type_val,
            title=title,
            status=status,
            detail=detail,
            instance=instance,
            extensions=extensions if extensions else None,
        )

    def to_exception_message(self) -> str:
        """Convert problem details to exception message."""
        lines = []

        # Add basic error info
        if self.title:
            lines.append(self.title)
        elif self.detail:
            lines.append(self.detail)

        # Add detail if we have a title
        if self.title and self.detail and self.title != self.detail:
            lines.append(self.detail)

        # Add problem type
        if self.type:
            lines.append(f"Problem Type: {self.type}")

        # Add instance
        if self.instance:
            lines.append(f"Instance: {self.instance}")

        # Add extension fields
        if self.extensions:
            lines.append("Extension fields:")
            for key, value in self.extensions.items():
                lines.append(f"  - {key}: {value}")

        return "\n".join(lines) if lines else "Unknown API error"
