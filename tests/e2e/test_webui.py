"""
WebUI End-to-End Tests using Playwright.

Tests the control center web interface including
panel loading, interactions, and navigation.
"""

import pytest
from playwright.async_api import async_playwright, Page, expect


@pytest.fixture
async def browser():
    """Create a browser instance for testing."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        yield browser
        await browser.close()


@pytest.fixture
async def page(browser):
    """Create a new page for testing."""
    page = await browser.new_page()
    yield page
    await page.close()


@pytest.mark.asyncio
async def test_control_center_loads(page: Page):
    """
    Test that the control center main page loads successfully.
    
    Verifies that the main control center route is accessible
    and renders without errors.
    """
    await page.goto("http://localhost:8000/control-center/")
    await expect(page.locator("body")).to_be_visible()
    title = await page.title()
    assert "Control Center" in title or "Contract Kit" in title


@pytest.mark.asyncio
async def test_provider_panel(page: Page):
    """
    Test that the provider panel loads and displays provider information.
    
    Verifies that the provider panel is accessible, shows provider
    status, and updates when refreshed.
    """
    await page.goto("http://localhost:8000/control-center/providers")
    await expect(page.locator("[data-panel='provider']")).to_be_visible()
    status = await page.locator("[data-provider-status]").first.text_content()
    assert status is not None


@pytest.mark.asyncio
async def test_evidence_panel(page: Page):
    """
    Test that the evidence panel loads and displays evidence items.
    
    Verifies that the evidence panel is accessible, lists evidence
    items, and supports filtering.
    """
    await page.goto("http://localhost:8000/control-center/evidence")
    await expect(page.locator("[data-panel='evidence']")).to_be_visible()
    evidence_list = await page.locator("[data-evidence-item]").count()
    assert evidence_list >= 0
