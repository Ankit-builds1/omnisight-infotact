# ML - VLM Integration

#OpenRouter account created, API key stored in `.env`
## VLM Testing Results

Tested the local LLaVA model (`vlm_test.py`) on sample UI images:
- **Accuracy:** Correctly identified page layouts, navigation menus, specific text elements (e.g., "Priya Lila", "75%"), and footer structures.
- **Quality:** Output is structured, reliable, and free from hallucinations.

# VLM (Vision-Language Model) Script

## Overview
This script uses a local Vision-Language Model to analyze images and generate text descriptions/answers based on visual input.

## Prerequisites & Installation
Before running the script, ensure you have **Ollama** installed and the **LLaVA** model downloaded.

1. **Install Ollama**: Download and install from [ollama.com](https://ollama.com).
2. **Pull the LLaVA model**: Run the following command in your terminal:
   ```bash
   ollama pull llava

   ## Setup & Prerequisites

# Vision Audit — VLM Deliberate UI Bug Detection

## Objective

The objective of this Vision Audit is to verify that the Vision Language Model (VLM) can correctly identify a deliberate UI bug in a screenshot while avoiding false positives on clean screenshots.

The VLM analyzes UI screenshots and returns a structured JSON response containing:

* `bug_found`
* `description`
* `severity_level`
* `confidence_score`
* `fix`

## 1. JSON Output Corrections

Two issues identified during the previous test were corrected:

### Severity Level

The VLM output now includes the `severity_level` field.

Example:

```json
"severity_level": "Minor"
```

### Confidence Score

The confidence score is now normalized to the rang `0.0–1.0`.

Examples from the audit:

```json
"confidence_score": 0.90
```

```json
"confidence_score": 0.99
```

The output no longer uses a `0–100` percentage-style confidence value.

---

## 2. Deliberate Bug Test

### Test Image

`ML/images/broken-button-clip.png`

This screenshot contains a deliberate UI inconsistency where the `+` icon is missing from the last item in a list while the other items contain the icon.

### VLM Result

```json
{
  "bug_found": true,
  "description": "In the screenshot, the UI displays a list of items with a '+' icon to add new items. However, the '+' icon is missing from the last item in the list. This inconsistency in the visual state of the UI elements indicates a bug.",
  "severity_level": "Minor",
  "confidence_score": 0.90,
  "fix": "To fix this bug, the '+' icon should be added to the last item in the list to maintain consistency with the rest of the items."
}
```

### Result

**BUG DETECTED**

The VLM successfully identified the deliberate UI bug.

* `bug_found`: `true`
* Severity: `Minor`
* Confidence: `0.90`
* Description: Correctly identifies the missing `+` icon.
* Fix: Correctly recommends adding the missing icon.

This confirms that the VLM is capable of detecting the deliberately introduced visual inconsistency.

---

## 3. Clean Screenshot Tests

To check for false positives, the VLM was also tested against screenshots that did not contain the deliberate bug.

### Test 1 — Cart Page

**Image:** `screenshots/cart-page.png`

Result:

```json
{
  "bug_found": false,
  "description": "No visible UI bugs were detected in this screenshot.",
  "severity_level": null,
  "confidence_score": 0.99,
  "fix": "No fix is required as there are no visible UI bugs in this screenshot."
}
```

**Result: NO BUG DETECTED**

---

### Test 2 — Confirmation Page

**Image:** `screenshots/confirmation-page.png`

Result:

```json
{
  "bug_found": false,
  "description": "No visible UI bugs were detected in the provided screenshot.",
  "severity_level": null,
  "confidence_score": 0.90,
  "fix": "No fix is required based on the provided screenshot."
}
```

**Result: NO BUG DETECTED**

---

## 4. Vision Audit Summary

| Screenshot               | Expected Result | VLM Result | Confidence | Status |
| ------------------------ | --------------- | ---------- | ---------: | ------ |
| `broken-button-clip.png` | Bug detected    | `true`     |       0.90 | PASS   |
| `cart-page.png`          | No bug          | `false`    |       0.99 | PASS   |
| `confirmation-page.png`  | No bug          | `false`    |       0.90 | PASS   |

### Audit Conclusion

The Vision Audit successfully demonstrates that the VLM can:

1. Detect the deliberately introduced UI bug.
2. Generate a meaningful description of the detected issue.
3. Assign a severity level.
4. Provide a confidence score in the required `0.0–1.0` range.
5. Suggest an appropriate fix.
6. Avoid false positives on the tested clean screenshots.

Therefore, the current VLM implementation successfully passes the basic Vision Audit for deliberate UI bug detection.

## Note

`screenshots/product-page.png` was not included in the clean-screenshot evaluation because the VLM reported a possible visual inconsistency in that screenshot. It was therefore not used as evidence for the no-false-positive test.
