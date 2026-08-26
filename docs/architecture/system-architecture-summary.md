# Idan Rent a Car — System Architecture & Business Logic Summary

## 1. Purpose

This document summarizes the full system-design discussion for a new operational platform for **Idan Rent a Car**. It is intended as a handoff document for someone who did not participate in the original discussion.

It explains:

- the business model,
- current operational needs,
- the desired workflow,
- the proposed data structure,
- pricing and supplier logic,
- quotes and bookings,
- sub-agents,
- employees and commissions,
- booking changes,
- settlement reconciliation,
- important rental rules,
- and the reasoning behind the main architecture decisions.

This is not yet a final database schema or software specification. It is a structured business/product architecture that can be used as the basis for UX, database, backend, and implementation planning.

---

# 2. Business context

Brand: **Idan Rent a Car**.

Business role: official representative / agent working with multiple Polish rental companies.

Current active suppliers:

- **Kaizen Rent**
- **One Rent**
- **Car Free**

The system must support adding, disabling, or replacing suppliers later without code changes.

The business primarily serves Israeli customers and works through several possible booking sources:

- direct clients,
- sub-agents,
- website-originated bookings,
- other sources.

The business is not intended to work like a fully automatic comparison engine. The operator normally chooses a small number of good options and sends a curated offer.

Core business value:

- personal service,
- negotiated pricing,
- transparent conditions,
- handling communication with rental companies,
- managing booking changes,
- helping with operational issues,
- and reconciling monthly supplier settlements and commissions.

---

# 3. Main goal of the new system

The current workflow is spreadsheet-heavy and time-consuming.

The new system should cover the full lifecycle:

1. customer inquiry,
2. customer lookup or creation,
3. quote preparation,
4. several offer options, potentially from different suppliers,
5. customer acceptance,
6. booking creation,
7. supplier booking email,
8. supplier confirmation / voucher,
9. booking changes,
10. active rental,
11. completed rental,
12. monthly supplier settlement,
13. reconciliation,
14. final owner commission,
15. employee commission,
16. sub-agent financial logic,
17. history and archive.

Main principle:

> **Data should be entered once and reused through the entire workflow.**

The application should be a responsive cloud web application usable on:

- desktop,
- tablet,
- mobile.

---

# 4. Core architecture principles

## 4.1 Configuration instead of hardcoding

Anything that can change over time should be editable from an admin/configuration layer.

Examples:

- suppliers,
- locations,
- vehicle groups,
- price lists,
- seasons,
- rental-duration bands,
- extras,
- extra fees,
- driver rules,
- STOP SALE restrictions,
- alerts,
- sub-agent terms,
- supplier commissions,
- employee commissions,
- VAT,
- quote templates,
- supplier email templates,
- settlement import mappings,
- statuses,
- permissions,
- numbering rules.

## 4.2 Versioning

Historical bookings must not change when current commercial rules change.

Relevant configuration should therefore support:

- `valid_from`,
- `valid_to`,
- active/inactive state,
- versioning where needed.

Quotes and bookings should store snapshots of commercially important applied values.

## 4.3 Audit trail

Manual changes must be logged.

Examples:

- manual discount,
- manual surcharge,
- price override,
- rule override,
- commission override,
- booking change,
- settlement adjustment.

## 4.4 Operator-first design

The system is intended for experienced operators.

It should:

- calculate,
- warn,
- validate,
- highlight conflicts,
- request acknowledgement where appropriate,

but should not aggressively auto-select suppliers or automatically sell alternatives.

---

# 5. Customers

## `customers`

Represents the final/end customer.

Suggested fields:

- `customer_id`
- `first_name`
- `last_name`
- `full_name_latin`
- `email`
- `phone_1`
- `phone_2`
- `phone_3`
- `country`
- `city`
- `address`
- `postal_code`
- `preferred_language`
- `preferred_supplier_id`
- `customer_status`
- `warning_level`
- `warning_text`
- `internal_note`
- `created_at`
- `updated_at`
- `created_by`

### Phone design

A separate normalized phone table was discussed and rejected as unnecessary for this business.

Instead:

- `phone_1` = primary phone,
- `phone_2` = optional,
- `phone_3` = optional.

If only one number exists, only `phone_1` is used.

### Customer search

Fast search should work by:

- email,
- phone,
- first name,
- last name.

### Important email rule

Customer email must **not** be globally unique.

Reason: a sub-agent may use one common email address while booking for many different final customers.

---

# 6. Customer events and warnings

## `customer_events`

Stores only notable or non-standard events.

Examples:

- cancellation,
- no-show,
- accident,
- damage,
- complaint,
- payment issue,
- late return,
- dispute,
- supplier preference,
- positive note,
- manual warning,
- other significant event.

Suggested fields:

- `event_id`
- `customer_id`
- `booking_id` optional
- `quote_id` optional
- `event_type`
- `event_date`
- `severity`
- `title`
- `description`
- `supplier_id`
- `created_by`
- `created_at`
- `is_warning`
- `is_resolved`
- `resolved_at`
- `resolution_note`

Routine successful rentals should not generate customer events automatically.

Routine booking changes belong to the booking, not to `customer_events`.

Warnings should be visible but should not automatically block an experienced operator unless a configured rule explicitly requires blocking.

---

# 7. Sub-agents

## `sub_agents`

A sub-agent is a separate business entity, not a customer.

Suggested fields:

- `sub_agent_id`
- `name`
- `company_name`
- `code_prefix`
- `email`
- `phone_1`
- `phone_2`
- `phone_3`
- `status`
- `default_currency`
- `internal_note`
- `created_at`
- `updated_at`

### Sub-agent code

Each sub-agent may have a unique letter prefix used in internal booking numbering.

Example:

`AB-2026-00451`

---

# 8. Sub-agent terms by rental company

## `sub_agent_supplier_terms`

This is a key requirement.

A sub-agent may have different commercial terms with different rental companies.

The business relationship is:

> **Sub-Agent + Rental Company → specific commercial conditions**

The interface must clearly display the **rental company name**, not only a technical `supplier_id`.

Suggested fields:

- `term_id`
- `sub_agent_id`
- `supplier_id`
- `supplier_name` for display
- `pricing_profile_id`
- `markup_type`
- `markup_value`
- `commission_type`
- `commission_value`
- `discount_type`
- `discount_value`
- `minimum_margin`
- `valid_from`
- `valid_to`
- `is_active`
- `note`

Example:

### Agent AB

**Kaizen Rent**
- commission: 8%
- markup: 0
- pricing profile: Kaizen Standard

**One Rent**
- commission: 6%
- markup: 3%

**Car Free**
- commission: 10%
- fixed markup: 100 PLN

These conditions must be versioned.

Historical bookings preserve the conditions that were valid when the booking was created.

---

# 9. Suppliers

## `suppliers`

Represents rental companies.

Suggested fields:

- `supplier_id`
- `supplier_code`
- `supplier_name`
- `legal_name`
- `status`
- `default_currency`
- `booking_email`
- `changes_email`
- `settlement_email`
- `phone`
- `website`
- `internal_note`
- `created_at`
- `updated_at`

Current suppliers:

- Kaizen Rent
- One Rent
- Car Free

The supplier table contains stable company information only.

Changing prices, commissions, rules, and terms belong in separate configuration tables.

---

# 10. Supplier locations

## `supplier_locations`

A location is always stored **in the context of a specific rental company**.

The same physical place can therefore exist multiple times in the system.

Example:

- Kaizen Rent — Kraków Airport
- One Rent — Kraków Airport
- Car Free — Kraków Airport

This is necessary because suppliers may differ in:

- meeting point,
- airport desk,
- meet-and-greet service,
- opening hours,
- pickup method,
- return method,
- after-hours conditions,
- service price,
- prepayment requirement,
- instructions.

Suggested fields:

- `location_id`
- `supplier_id`
- `supplier_name`
- `location_code`
- `location_name`
- `city`
- `country`
- `address`
- `location_type`
- `airport_code`
- `supports_pickup`
- `supports_return`
- `supports_delivery`
- `supports_after_hours`
- `requires_prepayment`
- `default_pickup_instructions`
- `default_return_instructions`
- `is_active`
- `internal_note`
- `created_at`
- `updated_at`

Suggested location types:

- `BRANCH`
- `AIRPORT`
- `HOTEL_DELIVERY`
- `SEASONAL_POINT`
- `CUSTOM_POINT`
- `OTHER`

The design must support custom and seasonal service points even if there is no permanent branch.

---

# 11. Location-specific rates

## `supplier_location_rates`

Stores service fees for a specific supplier at a specific location.

Suggested fields:

- `rate_id`
- `supplier_id`
- `supplier_name`
- `location_id`
- `location_name`
- `service_type`
- `price`
- `currency`
- `valid_from`
- `valid_to`
- `is_seasonal`
- `is_active`
- `note`

Example service types:

- Pickup
- Return
- Delivery
- Collection
- Other

---

# 12. Vehicle groups

## `vehicle_groups`

Vehicle groups belong to suppliers.

Suggested fields:

- `vehicle_group_id`
- `supplier_id`
- `supplier_name`
- `group_code`
- `group_name`
- `category`
- `body_type`
- `transmission`
- `seats`
- `doors`
- `luggage_volume_liters`
- `luggage_large`
- `luggage_small`
- `luggage_priority`
- `cargo_note`
- `fuel_type_note`
- `is_active`
- `display_order`
- `internal_note`
- `available_from`
- `available_to`
- `booking_open_from`

Body type examples:

- Sedan
- Hatchback
- SUV
- Estate / Wagon
- Minivan
- Van
- Pickup
- Coupe
- Cabrio
- Other

### Luggage

Luggage capacity is an important customer-facing parameter.

The system should support:

- approximate liters,
- large suitcase count,
- small suitcase count,
- practical notes.

### Availability dates

A vehicle group may become physically available only from a future date but may already be bookable for future rentals.

Therefore `booking_open_from` may differ from `available_from`.

---

# 13. Vehicle models inside groups

## `vehicle_group_models`

Suggested fields:

- `vehicle_group_model_id`
- `vehicle_group_id`
- `brand`
- `model`
- `is_active`
- `display_order`

The operator may show multiple realistic models for a group.

However:

> The exact vehicle model is not guaranteed.

The guaranteed commercial product is the vehicle class/group and its relevant characteristics.

---

# 14. Availability restrictions / STOP SALE

## `availability_restrictions`

STOP SALE belongs outside the price list.

Suggested fields:

- `restriction_id`
- `supplier_id`
- `supplier_name`
- `vehicle_group_id`
- `location_id` optional
- `restriction_type`
- `pickup_date_from`
- `pickup_date_to`
- `reason`
- `is_active`
- `created_at`
- `created_by`
- `note`

Restriction types:

- `STOP_SALE`
- `LIMITED`
- `OTHER`

Typical use:

> specific vehicle group + specific date range

---

# 15. Price lists

## `price_lists`

Represents a version of a supplier price list.

Suggested fields:

- `price_list_id`
- `supplier_id`
- `supplier_name`
- `name`
- `version`
- `effective_from`
- `effective_to`
- `currency`
- `status`
- `source_type`
- `source_file`
- `note`
- `created_at`
- `created_by`

Statuses:

- Draft
- Active
- Archived

Source types:

- Manual
- Excel

A new price list creates a new version rather than overwriting the old one.

---

# 16. Seasons inside price lists

## `price_list_seasons`

One price list may contain multiple present or future seasons.

Suggested fields:

- `season_id`
- `price_list_id`
- `season_name`
- `rental_date_from`
- `rental_date_to`
- `priority`
- `is_active`
- `note`

### Current pricing rule

The whole rental uses the season determined by the **pickup date**.

Even if the rental crosses into another season.

This rule should remain configurable rather than permanently hardcoded.

Conceptual setting:

`season_calculation_method = PICKUP_DATE`

---

# 17. Rental-duration bands

## `price_list_day_ranges`

Each supplier may define different duration bands.

Suggested fields:

- `day_range_id`
- `price_list_id`
- `label`
- `days_from`
- `days_to`
- `sort_order`
- `is_active`
- `note`

Example:

- 1–2 days
- 3–5 days
- 6–10 days
- 11–20 days
- 21+ days

The structure of a price list should be configured before entering rates.

---

# 18. Base rental rates

## `price_list_rates`

Suggested fields:

- `rate_id`
- `season_id`
- `vehicle_group_id`
- `day_range_id`
- `daily_rate`
- `currency`
- `is_active`
- `note`

Base formula:

> **Rental Days × Daily Rate**

---

# 19. Supplier extras

## `supplier_extras`

Extras should be dynamic.

Examples:

- hotel delivery,
- airport delivery,
- late pickup,
- late return,
- child seat,
- booster,
- cross-border,
- GPS,
- snow chains,
- young driver,
- one-way,
- additional driver,
- custom fee.

Suggested fields:

- `extra_id`
- `supplier_id`
- `supplier_name`
- `extra_code`
- `name`
- `category`
- `description`
- `is_active`

Adding a new extra must not require changing the database schema.

---

# 20. Extra pricing

## `supplier_extra_rates`

Suggested fields:

- `extra_rate_id`
- `extra_id`
- `supplier_id`
- `location_id` optional
- `calculation_type`
- `amount`
- `currency`
- `days_from`
- `days_to`
- `minimum_amount`
- `maximum_amount`
- `valid_from`
- `valid_to`
- `priority`
- `formula_config`
- `is_active`
- `note`

Calculation types:

- `FIXED`
- `PER_DAY`
- `PER_RENTAL`
- `PER_UNIT`
- `PER_DRIVER_DAY`
- `FORMULA`

The design should support quantity dimensions such as:

- per child seat,
- per driver,
- per matching driver,
- per day,
- per unit.

---

# 21. Supplier rule engine

## `supplier_rules`

Generic configurable rules.

Suggested fields:

- `rule_id`
- `supplier_id`
- `supplier_name`
- `rule_name`
- `rule_type`
- `condition_config`
- `vehicle_group_id` optional
- `vehicle_category_id` optional
- `location_id` optional
- `action_type`
- `extra_id` optional
- `can_override`
- `priority`
- `valid_from`
- `valid_to`
- `is_active`
- `customer_visible`
- `operator_message`
- `customer_message`

Possible actions:

- `ALLOW`
- `INFO`
- `WARNING`
- `WARNING_REQUIRES_ACK`
- `SURCHARGE`
- `BLOCK`

Conditions should support AND/OR logic.

Rules apply to all registered drivers, not just the main driver.

---

# 22. Example: Kaizen Young Driver rule

Current example:

Minimum age:

- 18 years

Minimum experience:

- 6 months

Young Driver if:

- age < 24,
- OR driving experience < 12 months.

Surcharge:

> **30 PLN × number of matching young drivers × rental days**

A young driver cannot rent premium categories under the current rule.

The system should warn or block according to the configured rule.

---

# 23. Informational quote alerts

## `quote_alerts`

Some information is better represented as an alert rather than a hard machine rule.

Suggested fields:

- `alert_id`
- `name`
- `supplier_id` optional / ALL
- `language`
- `alert_text`
- `severity`
- `show_condition`
- `mandatory`
- `sort_order`
- `valid_from`
- `valid_to`
- `is_active`

Optional split:

- `operator_message`
- `customer_message`

---

# 24. Cross-border alert

Cross-border information should appear in every customer quote, even if the customer initially says they do not plan to leave Poland.

Reason:

Unauthorized cross-border use may trigger penalties and may affect SCDW/insurance protection.

The quote should make clear that if travel plans change, the customer must contact the operator in advance so the cross-border option can be arranged.

---

# 25. Quote/document templates

## `document_templates`

Quotes should not be a hardcoded sequence of paragraphs.

Possible templates:

- Direct Customer
- Sub-Agent
- Short Offer
- Regular Customer
- VIP
- Custom

Templates should be:

- creatable,
- copyable,
- renameable,
- editable,
- archivable.

---

# 26. Template blocks

## `template_blocks`

Quotes are assembled from configurable blocks.

Suggested fields:

- `block_id`
- `template_id`
- `block_name`
- `block_type`
- `sort_order`
- `enabled`
- `requirement`
- `content`
- `visibility_rule`
- `style_config`
- `data_source`

Possible block types:

- `FREE_TEXT`
- `DYNAMIC_TEXT`
- `RENTAL_SUMMARY`
- `VEHICLE_OPTIONS`
- `INCLUDED_EXTRAS`
- `NOT_INCLUDED_EXTRAS`
- `PRICE`
- `DEPOSIT`
- `COMMISSION`
- `IMAGE`
- `LINK`
- `BUTTON`
- `SEPARATOR`
- `CUSTOM`

Requirement levels:

- `OPTIONAL`
- `DEFAULT`
- `MANDATORY`

For a specific quote, the operator should be able to reorder, edit, add, or remove blocks without changing the base template unless explicitly saved.

---

# 27. Quotes

## `quotes`

A quote represents the overall customer request.

Suggested fields:

- `quote_id`
- `quote_number`
- `customer_id`
- `sub_agent_id` optional
- `created_by_user_id`
- `assigned_to_employee_id`
- `template_id`
- `language`
- `status`
- `pickup_datetime`
- `return_datetime`
- `rental_days`
- `pickup_location_id`
- `pickup_location_text`
- `return_location_id`
- `return_location_text`
- `cross_border_requested`
- `customer_notes`
- `internal_notes`
- `sent_at`
- `accepted_at`
- `created_at`
- `updated_at`

Possible statuses:

- Draft
- Sent
- Accepted
- Rejected
- Cancelled
- Closed

---

# 28. Critical quote rule: one quote may contain multiple suppliers

This was an important correction in the design.

A quote does **not** belong to one supplier.

One quote may contain several options from different rental companies.

Example:

- Option 1 — Kaizen Rent / Compact / 1,850 PLN
- Option 2 — One Rent / SUV / 2,150 PLN
- Option 3 — Car Free / Estate / 2,050 PLN
- Option 4 — Kaizen Rent / SUV / 2,300 PLN

Therefore:

> `supplier_id` belongs to each `quote_option`, not to the quote itself.

Only after the customer selects one option does a single supplier become the supplier for the resulting booking.

---

# 29. Quote options

## `quote_options`

Each option is one commercial proposal within a quote.

Suggested fields:

- `quote_option_id`
- `quote_id`
- `supplier_id`
- `supplier_name`
- `vehicle_group_id`
- `vehicle_group_name_snapshot`
- `vehicle_models_snapshot`
- `luggage_info_snapshot`
- `total_price`
- `currency`
- `deposit_amount`
- `service_type_id`
- `service_note`
- `customer_note`
- `display_order`
- `is_recommended`
- `is_selected`

Each option therefore has its own:

- supplier,
- vehicle group,
- calculation,
- extras,
- deposit,
- service mode,
- supplier rules,
- sub-agent terms where relevant.

---

# 30. Service types

## `service_types`

Service mode is commercially relevant.

Possible values:

- `AIRPORT_DESK`
- `MEET_AND_GREET`
- `BRANCH_DESK`
- `HOTEL_DELIVERY`
- `SELF_RETURN`
- `CUSTOM`

Example:

One supplier may work through meet-and-greet while another operates a physical airport desk.

This can influence customer choice.

---

# 31. Quote calculation

## `quote_option_calculation`

Calculation is separate from the customer-facing quote presentation.

Suggested fields:

- `calculation_id`
- `quote_option_id`
- `price_list_id`
- `season_id`
- `day_range_id`
- `rental_days`
- `base_daily_rate`
- `base_total`
- `extras_total`
- `surcharges_total`
- `discounts_total`
- `sub_agent_adjustment`
- `final_total`
- `currency`
- `calculation_snapshot`
- `created_at`

Each quote option is calculated independently.

---

# 32. Calculation lines

## `calculation_lines`

Dynamic detailed calculation rows.

Suggested fields:

- `calculation_line_id`
- `calculation_id`
- `item_id`
- `description`
- `calculation_type`
- `quantity`
- `units`
- `unit_price`
- `total`
- `source`
- `is_manual_override`
- `note`
- `visibility_scope`

Examples:

- base rental,
- cross-border,
- child seat,
- young driver,
- chains,
- delivery,
- late pickup,
- one-way,
- manual discount,
- manual surcharge.

Manual price changes should be explicit calculation lines, not silent edits to the final total.

---

# 33. Calculation visibility

Suggested scopes:

- `INTERNAL_ONLY`
- `SUPPLIER_VISIBLE`
- `CUSTOMER_VISIBLE`
- `INTERNAL_AND_SUPPLIER`

Typical behavior:

- operator sees the full calculation,
- customer sees a single all-in total,
- supplier receives the detailed calculation/breakdown when the booking is created.

---

# 34. Quote workflow

Recommended flow:

1. Enter request data.
2. Calculate options across suppliers.
3. Review calculations.
4. Review warnings.
5. Select the best few options from one or more suppliers.
6. Build one quote.
7. Send quote.

The operator should be able to:

- inspect each calculation line,
- add an extra,
- remove an optional extra,
- change quantity,
- add manual discount,
- add manual surcharge,
- acknowledge warnings,
- recalculate.

---

# 35. Employees

## `employees`

Employees require a dedicated business entity because they may earn commission from bookings.

Suggested fields:

- `employee_id`
- `first_name`
- `last_name`
- `email`
- `phone`
- `role`
- `status`
- `login_user_id`
- `internal_note`
- `created_at`
- `updated_at`

Possible roles:

- `OWNER_ADMIN`
- `ADMIN`
- `SALES`
- `OPERATOR`
- `MANAGER`
- `OTHER`

The owner/admin is also a valid creator of quotes and bookings.

---

# 36. Employee commission rules

## `employee_commission_rules`

Employee commission must be configurable and versioned.

Suggested fields:

- `employee_commission_rule_id`
- `employee_id`
- `supplier_id` optional
- `booking_source_type` optional
- `sub_agent_id` optional
- `commission_type`
- `commission_value`
- `commission_basis`
- `valid_from`
- `valid_to`
- `priority`
- `is_active`
- `note`

Current example:

> An employee may receive **4% of Gross** for bookings assigned to that employee under current working conditions.

Future rules may differ by:

- employee,
- supplier,
- booking source,
- sub-agent,
- date range.

---

# 37. Creator vs salesperson/booking owner

These concepts should be separate.

### `created_by`

Who technically entered the record into the system.

### `salesperson_employee_id`

Who commercially owns the booking and receives employee commission.

Usually these may be the same person, but not always.

Example:

- Employee A handled the customer,
- Admin later entered the booking.

Employee A should still receive commission if the configured rule says so.

---

# 38. Bookings

## `bookings`

A booking is created from the customer's selected `quote_option`.

At this point there is one specific supplier.

Suggested fields:

- `booking_id`
- `booking_number`
- `supplier_booking_number`
- `quote_id`
- `quote_option_id`
- `customer_id`
- `sub_agent_id`
- `supplier_id`
- `supplier_name`
- `vehicle_group_id`
- `pickup_datetime`
- `return_datetime`
- `rental_days`
- `pickup_location_id`
- `pickup_location_text`
- `return_location_id`
- `return_location_text`
- `hotel_name`
- `hotel_address`
- `flight_number`
- `customer_email`
- `customer_address`
- `deposit_amount`
- `currency`
- `status`
- `created_by_user_id`
- `created_by_employee_id`
- `created_by_role_snapshot`
- `salesperson_employee_id`
- `employee_commission_rule_id`
- `employee_commission_rate_snapshot`
- `employee_commission_basis_snapshot`
- `assigned_to`
- `internal_notes`
- `created_at`
- `updated_at`

---

# 39. Booking source

The source of the customer/order is separate from the employee.

Suggested fields:

- `booking_source_type`
- `sub_agent_id`
- `sub_agent_code_snapshot`
- `commission_rule_id`
- `commission_rate_snapshot`

Source types:

- `DIRECT`
- `SUB_AGENT`
- `WEBSITE`
- `OTHER`

Examples:

- Employee A + Direct + Kaizen
- Employee A + Sub-Agent AB + One Rent
- Owner/Admin + Direct + Car Free

---

# 40. Phones in bookings

For a direct booking:

- send the final customer's phone.

For a sub-agent booking:

1. send the final customer's phone first,
2. send the sub-agent's phone as an additional fallback contact.

Booking snapshot fields:

- `customer_phone_snapshot`
- `sub_agent_phone_snapshot`

The sub-agent phone is populated only where relevant.

---

# 41. Supplier-facing contact format for sub-agent bookings

Preferred format:

**Customer phone:** +48 ...  
**Additional contact:** +972 ... *(Sub-agent)*

Operational logic:

- supplier first tries to contact the final customer,
- if the customer cannot be reached, supplier contacts the sub-agent,
- the sub-agent then handles the issue with the customer.

This is intentionally simple.

---

# 42. Booking drivers

## `booking_drivers`

Suggested fields:

- `booking_driver_id`
- `booking_id`
- `customer_id` optional
- `first_name`
- `last_name`
- `driver_role`
- `phone_snapshot`
- `display_order`
- `young_driver_status`
- `rule_warning`

Roles:

- Main
- Additional

All driver rules apply to all registered drivers.

---

# 43. Booking extras

## `booking_extras`

Suggested fields:

- `booking_extra_id`
- `booking_id`
- `extra_id`
- `quantity`
- `customer_visible_name`
- `supplier_visible_name`
- `price_snapshot`
- `included_in_total`

Can also store zero-price inclusions such as:

- Additional Driver — Included
- Unlimited Mileage — Included

---

# 44. Supplier booking email

When creating a booking, the supplier should receive a structured message containing:

1. names of all drivers,
2. final-customer phone,
3. for sub-agent booking: sub-agent phone marked `(Sub-agent)`,
4. email for voucher,
5. pickup date/time/place,
6. hotel name/address where relevant,
7. flight number for airport pickup,
8. return date/time/place,
9. rental days,
10. vehicle group/class,
11. extras and included conditions,
12. cross-border yes/no,
13. child seats, chains, additional drivers, etc.,
14. detailed calculation,
15. total price,
16. deposit,
17. customer address,
18. free comments.

The exact order and labels must be configurable per supplier.

---

# 45. Booking changes

## `booking_changes`

Changes belong to a specific booking.

Suggested fields:

- `booking_change_id`
- `booking_id`
- `change_number`
- `change_type`
- `requested_at`
- `requested_by`
- `status`
- `description`
- `old_snapshot`
- `requested_new_snapshot`
- `supplier_response`
- `sent_at`
- `confirmed_at`
- `created_by`
- `internal_note`

Statuses:

- Draft
- Sent
- Waiting
- Approved
- Rejected
- Cancelled

---

# 46. Booking change items

## `booking_change_items`

A single change request may contain several changes.

Suggested fields:

- `change_item_id`
- `booking_change_id`
- `field_type`
- `old_value`
- `new_value`
- `note`

Examples:

- return date,
- pickup time,
- location,
- vehicle group,
- additional driver,
- added/removed extra,
- cross-border.

---

# 47. Applying booking changes

Important rule:

> The main booking must remain the last supplier-confirmed state until the supplier approves the requested change.

Before approval:

- pending changes are shown separately.

After approval:

- apply changes to booking,
- create a new booking version.

---

# 48. Booking versions

## `booking_versions`

Examples:

- Version 1 — original confirmed booking
- Version 2 — after approved change #1
- Version 3 — after approved change #2

This preserves history.

The number of changes is counted per booking, not as a lifetime customer total.

---

# 49. Booking financials

## `booking_financials`

Financial state of a booking.

Core values:

- `quote_total`
- `confirmed_total`
- `settlement_total`
- `currency`
- `deposit_amount`

Owner/supplier commission:

- `supplier_commission_rule_id`
- `supplier_commission_rate_snapshot`
- `supplier_commission_amount`

Sub-agent:

- `sub_agent_commission_rule_id`
- `sub_agent_commission_rate_snapshot`
- `sub_agent_commission_amount`

Employee:

- `employee_id`
- `employee_commission_rule_id`
- `employee_commission_rate_snapshot`
- `employee_commission_basis_snapshot`
- `employee_commission_amount`

Settlement:

- `settlement_status`
- `settlement_id`
- `last_updated_at`

---

# 50. Three price levels

The system should distinguish three commercial values.

## Quote Total

What was offered to the customer.

## Confirmed Total

The current supplier-confirmed amount after approved booking changes.

## Settlement Total

The final amount recognized by the supplier during monthly settlement.

This distinction is essential for accurate financial reconciliation and commissions.

---

# 51. Owner/supplier commission rules

## `commission_rules`

The owner's commission from the rental supplier may vary.

Suggested fields:

- `commission_rule_id`
- `supplier_id`
- `supplier_name`
- `booking_source`
- `sub_agent_id` optional
- `commission_type`
- `commission_value`
- `amount_basis`
- `valid_from`
- `valid_to`
- `priority`
- `is_active`
- `note`

Current indicative examples:

- Direct client: around **12%**
- Sub-Agent booking: around **8%**
- Website booking: around **4%**

These are configurable examples, not hardcoded constants.

Rates may differ by supplier and over time.

---

# 52. Employee commission example

Example:

- final Gross booking amount: 10,000 PLN
- owner supplier commission: 12%
- employee commission: 4% Gross

Then:

- owner commission = 1,200 PLN
- employee commission = 400 PLN

These are separate calculations.

If settlement later reduces the recognized amount to 8,000 PLN:

- employee commission at 4% becomes 320 PLN.

If final recognized amount is 0:

- employee commission is 0.

---

# 53. Settlements

## `settlements`

Represents one supplier's monthly settlement/reconciliation period.

Suggested fields:

- `settlement_id`
- `supplier_id`
- `supplier_name`
- `period_from`
- `period_to`
- `settlement_month`
- `status`
- `source_file_name`
- `imported_at`
- `imported_by`
- `total_supplier_amount`
- `total_commission_expected`
- `total_commission_confirmed`
- `paid_at`
- `note`

Possible statuses:

- Uploaded
- Matching
- Review
- Approved
- Paid
- Closed

---

# 54. Settlement lines

## `settlement_lines`

Suggested fields:

- `settlement_line_id`
- `settlement_id`
- `supplier_booking_number`
- `booking_id`
- `customer_name_raw`
- `amount_net`
- `amount_gross`
- `vat_amount`
- `commission_amount_raw`
- `match_status`
- `difference_amount`
- `raw_data`
- `review_note`
- `is_approved`

The original supplier Excel row should be preserved in `raw_data`.

---

# 55. Reconciliation logic

Main match outcomes:

- `MATCHED`
- `PRICE_MISMATCH`
- `NOT_FOUND`
- `DUPLICATE`
- `REVIEW`
- `MISSING_FROM_SETTLEMENT`

Matching must work in both directions.

### Supplier file → internal system

Find:

- correct booking,
- amount mismatch,
- unknown booking,
- duplicate.

### Internal system → supplier file

Find internal bookings expected in the settlement but missing from the supplier file.

Possible reasons:

- cancellation,
- no-show,
- date change,
- supplier omission,
- booking number discrepancy,
- other issue.

Goal:

> Automate normal matches and force manual work only on exceptions.

---

# 56. VAT / tax rates

## `tax_rates`

VAT must not be hardcoded.

Suggested fields:

- `tax_rate_id`
- `country`
- `tax_name`
- `rate_percent`
- `valid_from`
- `valid_to`
- `is_active`

Example:

Polish VAT may currently be 23%, but the system must allow this to change over time.

---

# 57. Gross / Net settlement logic

Supplier Excel settlement files differ.

Some suppliers provide:

- Gross amount,
- Net amount,
- both,
- or another amount column that should be used for comparison.

The importer must allow the operator to define whether the selected comparison amount is:

- `GROSS`
- `NET`

If Gross:

> use Gross directly.

If Net:

> **Gross = Net × (1 + applicable VAT)**

Commission calculation then uses the configured amount basis.

The current business preference is generally to calculate from Gross.

---

# 58. Supplier settlement import configuration

## `supplier_settlement_config`

Suggested fields:

- `supplier_id`
- `supplier_name`
- `booking_number_column`
- `price_column`
- `price_basis`
- `net_column`
- `gross_column`
- `vat_column`
- `commission_column`
- `currency_column`
- `date_column`
- `customer_column`
- `tolerance`
- `is_active`

Before importing, the system should show a preview of several parsed rows including:

- booking number,
- selected comparison amount,
- Gross,
- Net,
- VAT,
- commission where available.

This protects against supplier Excel layout changes.

---

# 59. Dashboard

Suggested dashboard sections:

## Today

- pickups,
- returns,
- waiting supplier confirmations,
- pending changes,
- problem bookings.

## Upcoming

- future pickups,
- missing flight numbers,
- missing phones,
- missing vouchers,
- open booking changes.

## Finance

- settlements pending,
- price mismatches,
- missing bookings,
- unresolved settlement lines,
- supplier commissions,
- employee commissions,
- sub-agent financial items.

## Employees

- bookings by employee,
- Gross booking volume,
- settled volume,
- earned commission,
- unpaid employee commission.

---

# 60. Permissions

Role-based permissions should be supported.

Possible capabilities:

- create customer,
- create quote,
- calculate price,
- create booking,
- create booking change,
- see own bookings,
- see all bookings,
- override prices,
- see internal commissions/margins,
- work with settlements,
- edit configuration,
- manage users.

Admin-only examples:

- commission rules,
- VAT,
- supplier configuration,
- price-list configuration,
- settlement mappings,
- permissions.

---

# 61. Migration from existing Excel workflow

Recommended approach:

1. Choose a cutover date.
2. Keep old Excel files as archive/history.
3. Move only:
   - active bookings,
   - future bookings,
   - financially unsettled bookings.
4. From the cutover date onward, create new work only in the new system.
5. Avoid maintaining a permanent duplicate workflow in both Excel and the new platform.

Optional imports may be built for:

- price lists,
- current bookings,
- settlement files,
- customer data.

A full historical migration is not required for the first release.

---

# 62. Rental/business rules already identified

These rules may be represented through supplier rules, alerts, templates, or configuration.

## Insurance / SCDW

Customer package generally uses full SCDW / full waiver with zero excess, although terminology differs by supplier.

Typical coverage may include:

- theft,
- body damage,
- glass,
- tires,
- rims,
- mirrors,
- underbody,

subject to supplier conditions.

Common exclusions:

- gross negligence,
- drunk driving,
- intentional damage,
- wrong fuel,
- lost keys,
- off-road/non-paved use,
- unauthorized cross-border use where applicable.

## Deposit

Deposit is still blocked even with full SCDW.

Deposit:

- varies by supplier/class,
- is shown separately,
- is a card authorization/block, not rental cost.

## Payment

General rules:

- payment by card,
- Visa/Mastercard standard,
- AmEx supplier-dependent,
- physical card normally required,
- card should be in driver's name,
- debit usually accepted but supplier-specific,
- no cash for rental/deposit/extras,
- terminal amount in PLN,
- DCC/currency selection may appear.

## Driving license

- physical national driving license required,
- Israeli license generally sufficient in Poland,
- international permit may be recommended/informational depending destination and license,
- international permit alone is not a replacement for the national license.

## Mileage and fuel

- unlimited mileage,
- full-to-full fuel.

## Additional drivers

Typically up to two additional drivers may be free depending supplier terms.

Further drivers may be paid.

## Child seats

- paid extra,
- pre-order required,
- child age/weight required,
- parents/driver install the seat.

## GPS

Available but generally not recommended.

## Winter equipment

- winter or all-season tires in winter season,
- chains may be available as paid/preordered extra.

## Cross-border

- must be arranged in advance,
- current allowed area generally EU + Switzerland,
- unauthorized crossing may breach contract and affect SCDW,
- ferries generally allowed without separate ferry insurance.

## Prohibited use

Examples:

- smoking,
- animals,
- off-road use,
- commercial use,
- unregistered driver.

## Pickup

Airport booking normally requires flight number.

Hotel delivery requires:

- hotel name,
- full address,
- reachable phone.

## Flight delay

Where flight number is provided, supplier generally waits according to its operational procedure.

## Cancellation

For Poland pickups, current general rule:

- free cancellation at least 24 hours before pickup.

Other cases may vary by supplier/location.

## Early return

No refund.

## Extension

Requires:

- supplier approval / availability,
- prepayment before the extra period.

Late payment may cause immobilization.

## Late return

A few hours late may cause an additional rental day depending on supplier rules.

Rental days are based on 24-hour periods.

## Accident / damage

Operational flow:

1. contact supplier,
2. contact police where required,
3. contact Idan/operator.

Even minor accidents may require police documentation depending supplier rules.

For parking damage with unknown culprit:

- supplier is contacted first.

## Theft

Flow:

1. supplier,
2. police,
3. operator.

## Replacement vehicle

Replacement should not be lower than the booked class and should preserve practical requirements such as passenger and luggage capacity.

---

# 63. Correct end-to-end workflow

This is the latest corrected workflow.

1. Customer inquiry arrives.
2. Search for existing customer or create a new customer.
3. Identify who is handling the request:
   - Owner/Admin,
   - Employee A,
   - Employee B,
   - etc.
4. Identify booking source:
   - Direct,
   - Sub-Agent,
   - Website,
   - Other.
5. If Sub-Agent:
   - select the specific sub-agent.
6. Enter common request details:
   - pickup and return dates,
   - pickup and return locations,
   - passengers,
   - vehicle needs,
   - transmission,
   - luggage needs,
   - drivers,
   - extras,
   - cross-border if known,
   - child seats, etc.
7. Calculate possible options across **multiple suppliers**.
8. For every option independently apply:
   - supplier price list,
   - season,
   - rental-duration band,
   - supplier extras,
   - supplier rules,
   - supplier location costs,
   - sub-agent terms for that specific supplier where applicable,
   - deposit,
   - service type,
   - warnings.
9. Operator reviews calculations and warnings.
10. Operator selects several good options from one or more suppliers.
11. Build one customer quote containing those options.
12. Send quote.
13. Customer selects one option.
14. Only at this point does one supplier become the supplier of the booking.
15. Complete any missing booking details.
16. Create booking from the selected `quote_option`.
17. Store snapshots of:
   - supplier,
   - vehicle group,
   - price,
   - applied terms,
   - employee commission rule,
   - owner/supplier commission rule,
   - sub-agent conditions where relevant.
18. Generate supplier booking email.
19. Send supplier booking request.
20. Receive supplier confirmation / booking number / voucher.
21. Mark booking confirmed.
22. Process later booking changes as structured change requests.
23. Keep requested changes separate until supplier approval.
24. Create booking versions after every approved change.
25. Rental becomes active/completed.
26. Import supplier monthly settlement.
27. Match settlement against internal bookings.
28. Automatically confirm normal matches.
29. Review only mismatches/exceptions.
30. Set final `settlement_total`.
31. Calculate owner commission.
32. Calculate sub-agent financials where applicable.
33. Calculate employee commission.
34. Mark booking financially settled.
35. Preserve customer, booking, change, and financial history.

---

# 64. Simplified entity relationship overview

```text
Customer
  └── Quotes
       └── Quote Options
            ├── Supplier A
            ├── Supplier B
            └── Supplier C
                 ↓ customer selects one
               Booking
                 ├── Supplier
                 ├── Vehicle Group
                 ├── Drivers
                 ├── Extras
                 ├── Booking Changes
                 ├── Booking Versions
                 └── Booking Financials
                        └── Settlement
```

Parallel structures:

```text
Sub-Agent
  └── Sub-Agent Supplier Terms
        ├── Kaizen terms
        ├── One Rent terms
        └── Car Free terms
```

```text
Employee
  └── Employee Commission Rules
        └── Applied to bookings commercially owned by that employee
```

```text
Supplier
  ├── Locations
  ├── Location Rates
  ├── Vehicle Groups
  ├── Price Lists
  ├── Extras
  ├── Rules
  ├── Settlement Config
  └── Commission Rules
```

---

# 65. What should be configurable in Admin

Without code changes:

- Suppliers
- Supplier contacts
- Supplier locations
- Location rates
- Vehicle groups
- Vehicle models
- Price lists
- Seasons
- Day ranges
- Daily rates
- Extras
- Extra rates
- STOP SALE
- Supplier rules
- Customer alerts
- Sub-Agents
- Sub-Agent + Supplier terms
- Employees
- Employee commission rules
- Owner/supplier commission rules
- VAT rates
- Quote templates
- Template blocks
- Supplier email templates
- Settlement mappings
- Statuses
- Booking numbering
- Languages
- Permissions

---

# 66. Intentional simplifications

## Customer phone storage

No separate `customer_phones` table.

Use up to three phone fields directly in `customers`.

Reason:

- operational simplicity,
- no real need for unlimited phone numbers,
- cleaner UI.

## Supplier contact for sub-agent booking

Use a simple fallback structure:

1. final customer phone,
2. sub-agent phone marked `(Sub-agent)`.

## VAT

The system should not become a full tax/accounting platform.

VAT is mainly needed to normalize Gross/Net settlement values and calculate commission correctly.

## Quote supplier relationship

A quote is supplier-independent.

Each `quote_option` owns its supplier.

This matches the actual sales workflow and allows one offer to contain several rental companies.

---

# 67. Items that may still need final clarification later

The architecture is strong enough to continue into implementation planning, but these details can still be refined:

- exact internal booking-number format,
- exact employee commission variants,
- exact sub-agent markup/commission formulas,
- exact quote content by language,
- exact supplier email formats,
- which supplier rules should hard-block versus warn,
- settlement matching tolerance,
- exact permissions matrix,
- whether multiple customer emails are needed,
- whether supplier contacts need a separate normalized table,
- exact scope of first Excel migration/import.

These are implementation/configuration details, not fundamental architectural blockers.

---

# 68. Final product philosophy

The system should not try to replace the operator's judgment.

It should provide:

- reliable structured data,
- fast calculation,
- customer history,
- configurable supplier logic,
- clear warnings,
- flexible multi-supplier quotes,
- direct conversion from accepted quote to booking,
- structured supplier communication,
- controlled booking changes,
- automated settlement matching,
- accurate owner/sub-agent/employee commissions,
- full historical auditability.

The operator remains in control of:

- which options are offered,
- which supplier is appropriate for a specific request,
- whether a warning can be accepted,
- when a manual commercial adjustment is appropriate,
- how exceptional settlement cases are resolved.

The intended balance is:

> **automation for repetitive operational work, while keeping commercial judgment and exception handling in human hands.**
