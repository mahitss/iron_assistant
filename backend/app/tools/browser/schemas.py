"""Pydantic schemas and arguments for Kairo's Browser Control System."""

from typing import Any

from pydantic import BaseModel, Field


class BrowserNavigateArgs(BaseModel):
    """Arguments for the browser_navigate tool."""

    url: str = Field(
        ...,
        min_length=8,
        max_length=2000,
        description="Public HTTP or HTTPS URL to navigate to",
        examples=["https://github.com/mahitss/iron_assistant"],
    )
    session_id: str | None = Field(
        default=None,
        max_length=100,
        description="Active chat / browser session ID. If omitted, uses current agent session.",
    )


class BrowserInspectArgs(BaseModel):
    """Arguments for the browser_inspect tool."""

    session_id: str | None = Field(
        default=None,
        max_length=100,
        description="Active chat / browser session ID. If omitted, uses current agent session.",
    )


class BrowserClickArgs(BaseModel):
    """Arguments for the browser_click tool."""

    selector: str | None = Field(
        default=None,
        max_length=500,
        description="CSS selector identifying the element to click",
    )
    role: str | None = Field(
        default=None,
        max_length=50,
        description="Accessible ARIA role (e.g. 'button', 'link', 'tab')",
    )
    name: str | None = Field(
        default=None,
        max_length=200,
        description="Accessible element name or button label",
    )
    text: str | None = Field(
        default=None,
        max_length=200,
        description="Exact or partial visible text to click",
    )
    session_id: str | None = Field(
        default=None,
        max_length=100,
        description="Active chat / browser session ID. If omitted, uses current agent session.",
    )


class BrowserFillArgs(BaseModel):
    """Arguments for the browser_fill tool."""

    field: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Target form input field identified by label, placeholder, name, or selector",
        examples=["Search", "Username", "Query"],
    )
    value: str = Field(
        ...,
        max_length=2000,
        description="Non-sensitive text value to type into the field",
    )
    session_id: str | None = Field(
        default=None,
        max_length=100,
        description="Active chat / browser session ID. If omitted, uses current agent session.",
    )


class BrowserScreenshotArgs(BaseModel):
    """Arguments for the browser_screenshot tool."""

    session_id: str | None = Field(
        default=None,
        max_length=100,
        description="Active chat / browser session ID. If omitted, uses current agent session.",
    )
    full_page: bool = Field(
        default=False,
        description="Capture full scrollable page instead of only visible viewport",
    )


class PageElementInfo(BaseModel):
    """Information about an interactive or semantic page element."""

    tag: str
    role: str | None = None
    text: str = ""
    name: str | None = None
    type: str | None = None
    is_interactive: bool = True
    action_or_href: str | None = None


class PageInspectionResult(BaseModel):
    """Structured inspection summary of a loaded webpage."""

    url: str
    title: str
    visible_text: str
    headings: list[str] = Field(default_factory=list)
    links: list[dict[str, str]] = Field(default_factory=list)
    buttons: list[str] = Field(default_factory=list)
    forms: list[dict[str, Any]] = Field(default_factory=list)
    total_elements_found: int = 0


class BrowserActionResult(BaseModel):
    """Structured result returned from a browser action."""

    success: bool
    action: str
    session_id: str
    url: str = ""
    title: str = ""
    error: str | None = None
    approval_required: bool = False
    data: dict[str, Any] | None = None
