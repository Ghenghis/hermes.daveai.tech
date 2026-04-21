"""
WebUI Auto-Fill End-to-End Tests using Playwright.

Tests the control center web interface including all auto-fill
features for SpeechTab, ProvidersTab, and TrainingTab.
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


@pytest.fixture
async def control_center_page(page: Page):
    """Navigate to control center and verify it loads."""
    await page.goto("http://localhost:8000/control-center/")
    await expect(page.locator("body")).to_be_visible()
    return page


# =============================================================================
# SpeechTab Auto-Fill Tests
# =============================================================================

@pytest.mark.asyncio
async def test_speech_tab_loads(control_center_page: Page):
    """
    Test that the SpeechTab loads with all provider sections.
    
    Verifies the speech settings panel is accessible and shows
    all 5 speech provider auto-fill buttons.
    """
    page = control_center_page
    
    # Navigate to speech tab
    await page.click("[data-tab='speech']")
    await expect(page.locator("[data-panel='speech']")).to_be_visible()
    
    # Verify all speech provider sections exist
    providers = ['azure', 'google', 'openai', 'elevenlabs', 'polly']
    for provider in providers:
        await expect(
            page.locator(f"[data-speech-provider='{provider}']")
        ).to_be_visible()


@pytest.mark.asyncio
async def test_speech_azure_autofill(control_center_page: Page):
    """
    Test Azure Speech auto-fill button works.
    
    Verifies clicking the auto-fill button populates the
    Azure Speech API key and region fields.
    """
    page = control_center_page
    
    await page.click("[data-tab='speech']")
    await page.click("[data-speech-provider='azure'] [data-action='autofill']")
    
    # Verify fields are populated
    key_value = await page.input_value("[data-speech-provider='azure'] input[name='api_key']")
    assert key_value and len(key_value) > 10, "Azure API key should be auto-filled"
    
    region_value = await page.input_value("[data-speech-provider='azure'] input[name='region']")
    assert region_value, "Azure region should be auto-filled"


@pytest.mark.asyncio
async def test_speech_google_autofill(control_center_page: Page):
    """
    Test Google Cloud TTS auto-fill button works.
    
    Verifies clicking the auto-fill button populates the
    Google Cloud TTS API key field.
    """
    page = control_center_page
    
    await page.click("[data-tab='speech']")
    await page.click("[data-speech-provider='google'] [data-action='autofill']")
    
    key_value = await page.input_value("[data-speech-provider='google'] input[name='api_key']")
    assert key_value and len(key_value) > 10, "Google API key should be auto-filled"


@pytest.mark.asyncio
async def test_speech_elevenlabs_autofill(control_center_page: Page):
    """
    Test ElevenLabs auto-fill button works.
    
    Verifies clicking the auto-fill button populates the
    ElevenLabs API key field.
    """
    page = control_center_page
    
    await page.click("[data-tab='speech']")
    await page.click("[data-speech-provider='elevenlabs'] [data-action='autofill']")
    
    key_value = await page.input_value("[data-speech-provider='elevenlabs'] input[name='api_key']")
    assert key_value and len(key_value) > 10, "ElevenLabs API key should be auto-filled"


@pytest.mark.asyncio
async def test_speech_openai_autofill(control_center_page: Page):
    """
    Test OpenAI TTS auto-fill button works.
    
    Verifies clicking the auto-fill button populates the
    OpenAI TTS API key field.
    """
    page = control_center_page
    
    await page.click("[data-tab='speech']")
    await page.click("[data-speech-provider='openai'] [data-action='autofill']")
    
    key_value = await page.input_value("[data-speech-provider='openai'] input[name='api_key']")
    assert key_value and len(key_value) > 10, "OpenAI TTS API key should be auto-filled"


@pytest.mark.asyncio
async def test_speech_polly_autofill(control_center_page: Page):
    """
    Test AWS Polly auto-fill button works.
    
    Verifies clicking the auto-fill button populates the
    AWS Polly access key and secret fields.
    """
    page = control_center_page
    
    await page.click("[data-tab='speech']")
    await page.click("[data-speech-provider='polly'] [data-action='autofill']")
    
    access_key = await page.input_value("[data-speech-provider='polly'] input[name='access_key_id']")
    assert access_key and len(access_key) > 10, "AWS access key should be auto-filled"
    
    secret_key = await page.input_value("[data-speech-provider='polly'] input[name='secret_access_key']")
    assert secret_key and len(secret_key) > 10, "AWS secret key should be auto-filled"


# =============================================================================
# ProvidersTab Auto-Fill Tests
# =============================================================================

@pytest.mark.asyncio
async def test_providers_tab_loads(control_center_page: Page):
    """
    Test that the ProvidersTab loads with discovered keys section.
    
    Verifies the providers panel shows the discovered API keys
    section with auto-fill buttons.
    """
    page = control_center_page
    
    await page.click("[data-tab='providers']")
    await expect(page.locator("[data-panel='providers']")).to_be_visible()
    await expect(page.locator("[data-section='discovered-keys']")).to_be_visible()


@pytest.mark.asyncio
async def test_providers_siliconflow_autofill(control_center_page: Page):
    """
    Test SiliconFlow provider auto-fill from discovered keys.
    
    Verifies clicking auto-fill populates the SiliconFlow API key.
    """
    page = control_center_page
    
    await page.click("[data-tab='providers']")
    await page.click("[data-provider='siliconflow'] [data-action='autofill']")
    
    key_value = await page.input_value("[data-provider='siliconflow'] input[name='api_key']")
    assert key_value and len(key_value) > 10, "SiliconFlow API key should be auto-filled"


@pytest.mark.asyncio
async def test_providers_minimax_autofill(control_center_page: Page):
    """
    Test MiniMax provider auto-fill from discovered keys.
    
    Verifies clicking auto-fill populates the MiniMax API key.
    """
    page = control_center_page
    
    await page.click("[data-tab='providers']")
    await page.click("[data-provider='minimax'] [data-action='autofill']")
    
    key_value = await page.input_value("[data-provider='minimax'] input[name='api_key']")
    assert key_value and len(key_value) > 10, "MiniMax API key should be auto-filled"


@pytest.mark.asyncio
async def test_providers_github_autofill(control_center_page: Page):
    """
    Test GitHub token auto-fill from discovered keys.
    
    Verifies clicking auto-fill populates the GitHub token field.
    """
    page = control_center_page
    
    await page.click("[data-tab='providers']")
    await page.click("[data-provider='github'] [data-action='autofill']")
    
    token_value = await page.input_value("[data-provider='github'] input[name='token']")
    assert token_value and len(token_value) > 10, "GitHub token should be auto-filled"


# =============================================================================
# TrainingTab Auto-Fill Tests
# =============================================================================

@pytest.mark.asyncio
async def test_training_tab_loads(control_center_page: Page):
    """
    Test that the TrainingTab loads with HuggingFace section.
    
    Verifies the training panel shows the HuggingFace API key
    section with auto-fill button.
    """
    page = control_center_page
    
    await page.click("[data-tab='training']")
    await expect(page.locator("[data-panel='training']")).to_be_visible()
    await expect(page.locator("[data-section='huggingface']")).to_be_visible()


@pytest.mark.asyncio
async def test_training_huggingface_autofill(control_center_page: Page):
    """
    Test HuggingFace API key auto-fill.
    
    Verifies clicking auto-fill populates the HuggingFace token field.
    """
    page = control_center_page
    
    await page.click("[data-tab='training']")
    await page.click("[data-section='huggingface'] [data-action='autofill']")
    
    token_value = await page.input_value("[data-section='huggingface'] input[name='hf_token']")
    assert token_value and len(token_value) > 10, "HuggingFace token should be auto-filled"


# =============================================================================
# Visual Regression Tests
# =============================================================================

@pytest.mark.asyncio
async def test_speech_tab_visual_state(control_center_page: Page):
    """
    Visual regression test for SpeechTab.
    
    Captures screenshot of SpeechTab for visual comparison.
    """
    page = control_center_page
    
    await page.click("[data-tab='speech']")
    await page.wait_for_load_state("networkidle")
    
    # Take screenshot of speech panel
    await page.screenshot(
        path="test-artifacts/speech-tab.png",
        full_page=False
    )
    
    # Verify no console errors
    logs = await page.evaluate("() => { return window.consoleErrors || []; }")
    assert len(logs) == 0, f"Console errors detected: {logs}"


@pytest.mark.asyncio
async def test_providers_tab_discovered_keys_visual(control_center_page: Page):
    """
    Visual test for discovered keys section.
    
    Verifies discovered keys section renders properly with keys displayed.
    """
    page = control_center_page
    
    await page.click("[data-tab='providers']")
    await page.wait_for_load_state("networkidle")
    
    # Verify discovered keys are shown (masked)
    key_elements = await page.locator("[data-discovered-key]").count()
    assert key_elements > 0, "Should show discovered API keys"
    
    # Take screenshot
    await page.screenshot(
        path="test-artifacts/providers-tab-discovered.png",
        full_page=False
    )


# =============================================================================
# Integration Tests - Full Workflows
# =============================================================================

@pytest.mark.asyncio
async def test_full_autofill_workflow(control_center_page: Page):
    """
    Test complete auto-fill workflow across all tabs.
    
    Verifies that auto-filling all providers and saving works correctly.
    """
    page = control_center_page
    
    # Fill speech providers
    await page.click("[data-tab='speech']")
    for provider in ['azure', 'google', 'openai', 'elevenlabs', 'polly']:
        await page.click(f"[data-speech-provider='{provider}'] [data-action='autofill']")
        await page.wait_for_timeout(100)  # Small delay between fills
    
    # Fill AI providers
    await page.click("[data-tab='providers']")
    for provider in ['siliconflow', 'minimax', 'github']:
        await page.click(f"[data-provider='{provider}'] [data-action='autofill']")
        await page.wait_for_timeout(100)
    
    # Fill training
    await page.click("[data-tab='training']")
    await page.click("[data-section='huggingface'] [data-action='autofill']")
    
    # Save all settings
    await page.click("[data-action='save-all-settings']")
    
    # Verify success message
    await expect(page.locator("[data-notification='success']")).to_be_visible()


@pytest.mark.asyncio
async def test_autofill_with_validation_errors(control_center_page: Page):
    """
    Test auto-fill handles validation errors gracefully.
    
    Verifies that invalid/malformed keys show appropriate error messages.
    """
    page = control_center_page
    
    await page.click("[data-tab='speech']")
    
    # Try to save without filling (should show validation errors)
    await page.click("[data-speech-provider='azure'] [data-action='save']")
    
    # Verify validation error appears
    await expect(page.locator("[data-error='validation-failed']")).to_be_visible()


@pytest.mark.asyncio
async def test_autofill_persists_after_refresh(control_center_page: Page):
    """
    Test that auto-filled settings persist after page refresh.
    
    Verifies settings are saved to backend and reloaded correctly.
    """
    page = control_center_page
    
    # Fill a setting
    await page.click("[data-tab='speech']")
    await page.click("[data-speech-provider='azure'] [data-action='autofill']")
    await page.click("[data-speech-provider='azure'] [data-action='save']")
    
    # Wait for save confirmation
    await expect(page.locator("[data-notification='saved']")).to_be_visible()
    
    # Refresh page
    await page.reload()
    await page.wait_for_load_state("networkidle")
    
    # Navigate back to speech tab
    await page.click("[data-tab='speech']")
    
    # Verify value persisted
    key_value = await page.input_value("[data-speech-provider='azure'] input[name='api_key']")
    assert key_value and len(key_value) > 10, "Setting should persist after refresh"
