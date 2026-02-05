"""
MODULES LAYER CONTRACT

This package contains UI modules and presentation layer components.

RULES:
- Contains PyQt5/Qt widgets and UI components
- Implements presentation logic and user interaction
- May import from services layer for business logic
- No direct database or infrastructure access
- UI-specific exceptions and error handling

LAYER RESPONSIBILITY:
- User interface implementation
- Widget composition and layout
- Event handling and signal/slot connections
- Presentation model adaptation

CROSS-LAYER RESTRICTIONS:
- No business logic implementation
- No direct persistence operations
- No infrastructure dependencies
- Use services layer for all business operations

If you need business logic — delegate to services layer through interfaces.
"""