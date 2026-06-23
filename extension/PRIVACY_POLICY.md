# Privacy Policy — ZDrive Neuro Lens

**Last updated:** 2026-06-23

## What the extension does

ZDrive Neuro Lens is a Chrome extension that analyzes webpage text to detect manipulation patterns. It reads visible text from web pages you visit and sends it to our backend for scoring.

## Data we collect

**Page text:** When you scroll a webpage or open the side panel, the extension extracts visible text from the page (headlines, paragraphs, article content). This text is sent to our servers for analysis.

**Analysis results:** Manipulation scores and breakdown data are cached temporarily in your browser session. This cache is cleared when you close the browser.

**API key:** Your ZDrive API key is stored locally on your device (chrome.storage.local). It is not synced across devices.

## Data we do NOT collect

- Browsing history
- Personal information (name, email, address)
- Cookies or tracking identifiers
- Form data, passwords, or login credentials
- Screenshots or images from pages
- Data from non-active tabs

## How data is processed

1. Page text is sent via HTTPS to our backend servers for scoring.
2. Fast scans are processed by an LLM running in a Trusted Execution Environment (TEE).
3. Deep scans are processed by neural inference on dedicated GPU hardware.
4. Scores are returned to the extension and displayed in the side panel.
5. Page text is not stored on our servers after scoring. Results may be cached briefly in server memory for performance.

## Third-party services

- **Chutes AI** (llm.chutes.ai): Processes fast scan text via Qwen3-32B in a Trusted Execution Environment.
- **Modal** (modal.com): Processes deep scan text via TRIBE v2 neural inference on A10G GPU.
- **Cloudflare Workers**: Routes and authenticates API requests.
- **Fly.io**: Hosts the deep scan proxy server.

No third-party analytics, advertising, or tracking services are used.

## Permissions

- **Read page content** (`<all_urls>` content script): Required to extract visible text for analysis. The extension does not modify page content beyond adding a small score badge overlay.
- **Storage** (`storage`): Stores your settings and API key locally.
- **Side panel** (`sidePanel`): Displays analysis results.
- **Active tab** (`activeTab`): Identifies which page to scan.

## Data retention

- Page text: Not retained after scoring.
- Analysis results: Cached in browser session storage only. Cleared on browser close.
- API key: Stored locally until you remove it.

## Contact

For questions about this privacy policy: kwame.laryea@gmail.com

## Changes

We may update this privacy policy. Changes will be noted with an updated date at the top of this document.
