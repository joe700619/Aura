---
description: Comprehensive guide to the Aura ERP project architecture, directory structure, and module organization.
---

# Project Architecture & Directory Structure

This document outlines the architectural conventions used in the Aura ERP project. Adhering to these standards ensures maintainability, scalability, and consistency across the application.

## 1. High-Level Structure

The project follows a modular Django architecture, separating core functionality, business logic, and shared utilities.

*   **`modules/`**: Contains all business-logic applications (e.g., Bookkeeping, Basic Data, HR). This is where the core domain logic resides.
*   **`core/`**: Contains foundational, project-wide functionality that is not specific to a single business domain (e.g., Authentication, System Config, Audit Logs).
*   **`shared/`**: A utility layer for pure technical functions, constants, and helpers that can be used by any app (e.g., Date utils, String formatters).
*   **`templates/`**: The global template directory for shared layouts, components, and pages that don't belong to a specific module.
*   **`static/`**: Global static files (CSS, JS, Images).

## 2. Module Structure (`modules/`)

Each app within `modules/` (e.g., `bookkeeping`, `basic_data`) should follow this expanded structure to avoid monolithic files:

```text
modules/[app_name]/
├── models/                 # Split models into separate files
│   ├── __init__.py         # Expose models here
│   ├── [entity_a].py       # e.g., customer.py
│   └── [entity_b].py       # e.g., supplier.py
├── views/                  # Split views by domain entity
│   ├── __init__.py         # Expose views here
│   ├── [entity_a].py       # e.g., customer_views.py
│   └── [entity_b].py
├── services/               # Business logic layer (Thin Views, Fat Services)
│   ├── [entity_service].py # e.g., vat_service.py
│   └── ...
├── workflows/              # Complex state machine or multi-step process logic
│   ├── [process_name].py  # e.g., tax_filing_workflow.py
│   └── ...
├── templates/              # App-specific templates
│   └── [app_name]/         # Namespace templates to avoid conflicts
│       ├── [entity]/       # Sub-directory per entity
│       │   ├── list.html
│       │   ├── form.html
│       │   └── ...
├── urls.py                 # App-specific URL routing
└── apps.py                 # App configuration
```

### Example: Bookkeeping Module

```text
modules/bookkeeping/
├── models/
│   ├── vat.py              # VAT Declaration model
│   ├── income_tax.py       # Corporate Income Tax model
│   ├── withholding.py      # Withholding Tax model
│   └── progress.py         # Progress tracking model
├── services/
│   ├── vat_service.py      # Logic for VAT calculations and validation
│   ├── income_tax_service.py
├── workflows/
│   └── tax_filing.py       # Workflow for the tax filing process
├── views/
│   ├── vat.py              # Views for VAT list, detailed, edit
│   └── income_tax.py
├── urls.py
└── templates/
    └── bookkeeping/
        ├── vat/
        │   ├── list.html
        │   └── form.html
```

## 3. Core System (`core/`)

Functionality that "powers" the system but isn't part of the business domain.

*   **`auth/`**: Custom User model, Groups, Permissions.
*   **`system_config/`**: Dynamic settings, Menu management (`MenuItem`).
*   **`documents/`**: (Future) Engines for generating Word/Excel reports.
*   **`notifications/`**: System-wide notification center.

## 4. Shared Utilities (`shared/`)

Pure Python helpers, devoid of business logic.

*   **`constants.py`**: Global enums and constant values.
*   **`utils.py`**: Generic helper functions.
*   **`mixins.py`**: Shared Django model/view mixins (e.g., `TimestampMixin`).

## 5. Templates (`templates/`)

Global templates that define the look and feel.

*   **`base.html`**: The master layout file.
*   **`layouts/`**: Structural components.
    *   `topbar.html`: Header and user navigation.
    *   `sidebar.html`: Dynamic navigation menu.
    *   `footer.html`
*   **`components/`**: Reusable UI widgets.
    *   `list_view.html`: Standard layout for data tables (search, filter, pagination).
    *   `form_modal.html`: Standard modal forms.
    *   `row_checkbox.html`: The standard Checkbox UI for list rows.
    *   `row_actions.html`: The standard Edit/Delete buttons for list rows.

---

# CRITICAL CHECKLIST FOR AGENT

Before completing any task related to creating or modifying a full module, you **MUST** verify the following:

### 1. Model Definition
- [ ] Are you creating a new Model? If so, it **MUST** inherit from `BaseModel` located in `core.models`.
    - **WRONG**: `class MyModel(models.Model):`
    - **CORRECT**: `from core.models import BaseModel` -> `class MyModel(BaseModel):`
- [ ] Have you verified that you did *not* manually add `is_deleted`, `created_at`, `updated_at`, or `history`? (These are automatically provided by `BaseModel`).

### 2. List Template (`list.html`)
- [ ] Does the `<table>` row's checkbox use the standard component?
    - **REQUIRED**: `{% include "components/row_checkbox.html" with value=instance.pk %}`
    - **DO NOT** manually write out the Alpine.js checkbox HTML logic.
- [ ] Does the `<table>` row's action column use the standard component (if applicable)?
    - **REQUIRED**: `{% include "components/row_actions.html" with update_url=... delete_url=... %}`

By checking these items, you prevent common errors such as missing history tracking, broken soft delete, and broken checkbox bindings.
