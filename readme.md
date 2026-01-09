# Capital Selection Indicators

A prototype NVDA add-on that implements capital letter indicators for text selection.

## Purpose

This add-on is a **proof-of-concept implementation** for:
- [Issue #4874](https://github.com/nvaccess/nvda/issues/4874)
- [Issue #12996](https://github.com/nvaccess/nvda/issues/12996)

## Feature

When selecting single characters (e.g., using `Shift+Arrow`), NVDA will now announce capital letters with the same indicators used during character-by-character navigation:

- **Beep for capitals** - A short beep before uppercase letters
- **Say "cap" before capitals** - The word "cap" spoken before uppercase letters
- **Capital pitch change** - Higher pitch when speaking uppercase letters

## Configuration

**This plugin has no settings.** It follows your existing NVDA voice settings:

1. Open NVDA Menu → Preferences → Settings → Speech
2. Configure your capital letter preferences:
   - "Capital pitch change percentage"
   - "Say 'cap' before capitals"
   - "Beep for capitals"

The plugin respects these settings automatically.
