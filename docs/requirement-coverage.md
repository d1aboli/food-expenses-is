# Покриття вимог тестами

Звіт формується автоматично: `python tools/requirement_coverage.py` (REQ-NF-002).

| Показник | Кількість |
|---|---|
| Вимог оголошено | 64 |
| Покрито тестами | 50 |
| Перевіряються процесом, а не тестом | 9 |
| Поза обсягом ЛР5 | 5 |
| Без покриття | 0 |

## Вимоги, покриті тестами

| Вимога | Тестів | Тести |
|---|---|---|
| REQ-F-001 | 8 | test_profiles.py::test_profile_is_created_with_the_given_name<br>test_profiles.py::test_created_profile_response_carries_location_header<br>test_profiles.py::test_profile_name_must_be_unique<br>test_profiles.py::test_profile_with_blank_name_is_rejected<br>test_profiles.py::test_profile_without_name_field_is_rejected<br>test_profiles.py::test_profile_name_longer_than_sixty_characters_is_rejected<br>test_profiles.py::test_profile_name_keeps_leading_and_trailing_spaces_trimmed<br>test_profiles.py::test_profile_creation_is_written_to_the_action_log |
| REQ-F-002 | 3 | test_profiles.py::test_created_profiles_appear_in_the_list<br>test_profiles.py::test_single_profile_is_available_by_its_identifier<br>test_profiles.py::test_unknown_profile_identifier_is_reported_as_not_found |
| REQ-F-003 | 7 | test_categories.py::test_categories_of_one_profile_are_not_visible_in_another<br>test_categories.py::test_categories_of_unknown_profile_are_reported_as_not_found<br>test_categories.py::test_category_of_another_profile_cannot_be_renamed<br>test_export.py::test_export_of_an_unknown_profile_is_not_found<br>test_profiles.py::test_profiles_are_stored_independently_of_each_other<br>test_purchases.py::test_purchases_of_one_profile_are_invisible_in_another<br>test_summary.py::test_summary_counts_only_the_purchases_of_its_own_profile |
| REQ-F-004 | 1 | test_profiles.py::test_profile_list_is_empty_before_the_first_profile_is_created |
| REQ-F-005 | 4 | test_purchases.py::test_purchase_is_created_with_name_category_price_and_quantity<br>test_purchases.py::test_created_purchase_response_carries_location_header<br>test_purchases.py::test_purchase_cannot_be_added_to_a_category_of_another_profile<br>test_purchases.py::test_purchase_creation_is_written_to_the_action_log |
| REQ-F-006 | 4 | test_money.py::test_amount_for_weighted_purchase_from_acceptance_criteria<br>test_money.py::test_amount_is_rounded_half_up<br>test_money.py::test_amount_for_whole_quantity_equals_price<br>test_purchases.py::test_purchase_amount_is_price_multiplied_by_quantity |
| REQ-F-007 | 2 | test_purchases.py::test_purchase_time_is_set_by_the_server<br>test_purchases.py::test_client_cannot_set_the_time_while_adding_a_purchase |
| REQ-F-008 | 3 | test_purchases.py::test_purchase_fields_can_be_changed_and_amount_is_recalculated<br>test_purchases.py::test_purchase_time_can_be_changed<br>test_purchases.py::test_purchase_category_can_be_changed |
| REQ-F-009 | 3 | test_purchases.py::test_changing_the_date_moves_the_purchase_between_periods<br>test_summary.py::test_totals_are_recalculated_after_a_purchase_is_deleted<br>test_summary.py::test_totals_follow_the_purchase_when_its_date_changes |
| REQ-F-010 | 2 | test_purchases.py::test_purchase_is_deleted<br>test_purchases.py::test_deleting_an_unknown_purchase_is_reported_as_not_found |
| REQ-F-011 | 1 | test_purchases.py::test_identical_purchases_are_two_different_records |
| REQ-F-012 | 5 | test_purchases.py::test_purchases_are_listed_from_newer_to_older<br>test_purchases.py::test_single_purchase_is_available_by_its_identifier<br>test_purchases.py::test_unknown_purchase_is_reported_as_not_found<br>test_purchases.py::test_purchases_can_be_filtered_by_category<br>test_purchases.py::test_purchase_list_is_paginated_and_reports_the_total |
| REQ-F-013 | 3 | test_validation.py::test_purchase_with_non_positive_price_is_rejected<br>test_validation.py::test_price_that_is_not_a_number_is_rejected<br>test_validation.py::test_price_rules_apply_to_changes_as_well |
| REQ-F-014 | 2 | test_validation.py::test_purchase_with_non_positive_quantity_is_rejected<br>test_validation.py::test_quantity_rules_apply_to_changes_as_well |
| REQ-F-015 | 2 | test_validation.py::test_purchase_with_blank_name_is_rejected<br>test_validation.py::test_purchase_name_longer_than_hundred_characters_is_rejected |
| REQ-F-016 | 4 | test_validation.py::test_purchase_cannot_be_moved_into_the_future<br>test_validation.py::test_rejected_date_change_leaves_the_purchase_untouched<br>test_validation.py::test_purchase_time_in_the_past_is_accepted<br>test_validation.py::test_unparsable_date_is_rejected |
| REQ-F-017 | 3 | test_validation.py::test_price_with_more_than_two_decimal_places_is_rejected<br>test_validation.py::test_price_without_kopiikas_is_rejected_by_the_contract_format<br>test_validation.py::test_price_has_no_upper_limit |
| REQ-F-018 | 4 | test_money.py::test_amount_for_three_decimal_quantity<br>test_money.py::test_quantity_is_formatted_without_trailing_zeros<br>test_validation.py::test_quantity_with_three_decimal_places_is_accepted<br>test_validation.py::test_quantity_with_four_decimal_places_is_rejected |
| REQ-F-019 | 4 | test_infrastructure.py::test_error_body_matches_contract_error_schema<br>test_money.py::test_unparsable_price_is_rejected_with_the_field_name<br>test_money.py::test_unparsable_quantity_is_rejected_with_the_field_name<br>test_validation.py::test_rejection_message_is_in_ukrainian_and_names_the_requirement |
| REQ-F-020 | 2 | test_categories.py::test_new_profile_gets_the_five_base_categories<br>test_categories.py::test_base_categories_start_without_purchases |
| REQ-F-021 | 9 | test_categories.py::test_custom_category_is_created<br>test_categories.py::test_category_name_must_be_unique_within_the_profile<br>test_categories.py::test_category_name_collides_with_a_base_category<br>test_categories.py::test_same_category_name_is_allowed_in_another_profile<br>test_categories.py::test_category_with_blank_name_is_rejected<br>test_categories.py::test_category_name_longer_than_forty_characters_is_rejected<br>test_categories.py::test_category_cannot_be_created_in_unknown_profile<br>test_categories.py::test_unknown_category_is_reported_as_not_found<br>test_categories.py::test_category_creation_is_written_to_the_action_log |
| REQ-F-022 | 3 | test_categories.py::test_category_is_renamed_and_keeps_its_identifier<br>test_categories.py::test_category_cannot_be_renamed_to_an_existing_name<br>test_category_deletion.py::test_renamed_category_keeps_its_purchases |
| REQ-F-023 | 3 | test_categories.py::test_empty_category_is_deleted_without_confirmation<br>test_category_deletion.py::test_category_reports_the_number_of_its_purchases<br>test_category_deletion.py::test_non_empty_category_is_not_deleted_without_confirmation |
| REQ-F-024 | 3 | test_category_deletion.py::test_confirmed_deletion_moves_purchases_to_the_system_category<br>test_category_deletion.py::test_confirmed_deletion_keeps_the_purchases_themselves<br>test_category_deletion.py::test_moving_purchases_to_the_system_category_is_written_to_the_action_log |
| REQ-F-025 | 3 | test_categories.py::test_only_the_other_category_is_marked_as_system<br>test_categories.py::test_system_category_cannot_be_renamed<br>test_categories.py::test_system_category_cannot_be_deleted_even_with_confirmation |
| REQ-F-026 | 2 | test_summary.py::test_daily_total_counts_only_that_day<br>test_summary.py::test_unknown_period_is_a_bad_request |
| REQ-F-027 | 2 | test_summary.py::test_weekly_total_runs_from_monday_to_sunday<br>test_summary.py::test_week_boundaries_are_the_same_for_any_day_inside_it |
| REQ-F-028 | 1 | test_summary.py::test_monthly_total_runs_from_the_first_to_the_last_day |
| REQ-F-029 | 6 | test_export.py::test_export_with_unparsable_dates_is_a_bad_request<br>test_summary.py::test_range_includes_both_boundary_days<br>test_summary.py::test_range_of_a_single_day_is_allowed<br>test_summary.py::test_range_with_reversed_boundaries_is_a_bad_request<br>test_summary.py::test_range_without_boundaries_is_a_bad_request<br>test_validation.py::test_unparsable_date_range_is_a_bad_request |
| REQ-F-030 | 3 | test_summary.py::test_category_breakdown_shows_amount_and_share<br>test_summary.py::test_category_shares_add_up_to_one_hundred_percent<br>test_summary.py::test_breakdown_skips_categories_without_purchases |
| REQ-F-031 | 4 | test_charts.py::test_daily_chart_has_one_point_for_every_day_of_the_month<br>test_charts.py::test_daily_chart_bar_equals_the_total_of_that_day<br>test_charts.py::test_daily_chart_length_follows_the_length_of_the_month<br>test_charts.py::test_daily_chart_rejects_an_unparsable_month |
| REQ-F-032 | 4 | test_charts.py::test_monthly_chart_has_one_point_for_every_month_of_the_year<br>test_charts.py::test_monthly_chart_bar_equals_the_total_of_that_month<br>test_charts.py::test_monthly_chart_does_not_mix_years<br>test_charts.py::test_monthly_chart_rejects_an_unparsable_year |
| REQ-F-033 | 4 | test_charts.py::test_daily_chart_of_an_empty_month_has_only_zero_bars<br>test_export.py::test_export_of_an_empty_period_has_only_the_header<br>test_summary.py::test_empty_period_returns_zero<br>test_summary.py::test_breakdown_for_empty_period_is_empty |
| REQ-F-034 | 2 | test_infrastructure.py::test_migration_creates_tables_for_profiles_categories_and_purchases<br>test_infrastructure.py::test_migration_is_idempotent |
| REQ-F-035 | 5 | test_export.py::test_export_has_one_row_per_purchase<br>test_export.py::test_export_amounts_match_the_purchase_list<br>test_export.py::test_export_is_returned_as_a_csv_attachment<br>test_export.py::test_export_covers_only_the_requested_period<br>test_export.py::test_export_is_written_to_the_action_log |
| REQ-F-036 | 4 | test_export.py::test_backup_is_created<br>test_export.py::test_backup_contains_the_stored_data<br>test_export.py::test_repeated_backups_do_not_overwrite_each_other<br>test_export.py::test_backup_is_written_to_the_action_log |
| REQ-NF-005 | 2 | test_infrastructure.py::test_test_run_journal_records_date_and_counts<br>test_infrastructure.py::test_test_run_journal_keeps_previous_records |
| REQ-NF-008 | 2 | test_infrastructure.py::test_runtime_error_is_written_to_error_log_with_date_and_text<br>test_infrastructure.py::test_error_log_does_not_collect_ordinary_actions |
| REQ-NF-009 | 1 | test_performance.py::test_monthly_summary_on_ten_thousand_purchases_is_under_one_second |
| REQ-NF-010 | 4 | test_money.py::test_amount_does_not_lose_kopiikas_on_repeated_price<br>test_money.py::test_money_is_formatted_with_two_decimal_places<br>test_money.py::test_price_is_parsed_without_binary_floating_point<br>test_purchases.py::test_purchase_amount_keeps_kopiikas |
| REQ-I-003 | 2 | test_export.py::test_export_starts_with_the_agreed_header<br>test_export.py::test_export_is_utf8_and_keeps_ukrainian_names |
| REQ-A-001 | 5 | test_budgets.py::test_budget_is_set_for_a_category<br>test_budgets.py::test_set_budget_appears_in_the_list<br>test_budgets.py::test_created_budget_response_carries_location_header<br>test_budgets.py::test_budget_for_unknown_category_is_rejected<br>test_budgets.py::test_setting_a_budget_is_written_to_the_action_log |
| REQ-A-002 | 2 | test_budgets.py::test_budget_must_be_greater_than_zero<br>test_budgets.py::test_budget_without_kopiikas_is_rejected |
| REQ-A-003 | 1 | test_budgets.py::test_category_cannot_have_two_budgets |
| REQ-A-004 | 4 | test_budgets.py::test_budget_shows_spending_and_remainder_for_the_month<br>test_budgets.py::test_spending_of_another_category_does_not_affect_the_budget<br>test_budgets.py::test_budget_month_defaults_to_the_current_one<br>test_budgets.py::test_budget_list_rejects_an_unparsable_month |
| REQ-A-005 | 2 | test_budgets.py::test_exceeded_budget_is_marked_and_reports_the_excess<br>test_budgets.py::test_spending_of_another_month_does_not_affect_the_budget |
| REQ-A-006 | 2 | test_budgets.py::test_budget_amount_can_be_changed<br>test_budgets.py::test_changed_budget_must_also_be_greater_than_zero |
| REQ-A-007 | 2 | test_budgets.py::test_budget_is_deleted_and_purchases_stay<br>test_budgets.py::test_unknown_budget_is_reported_as_not_found |
| REQ-A-008 | 1 | test_budgets.py::test_deleting_a_category_deletes_its_budget |
| REQ-A-009 | 2 | test_budgets.py::test_budgets_of_one_profile_are_invisible_in_another<br>test_budgets.py::test_budgets_of_unknown_profile_are_reported_as_not_found |

## Вимоги процесу

| Вимога | Чим перевіряється |
|---|---|
| REQ-NF-001 | порядок «тест раніше за код» — історія Git і logs/test-gate.md |
| REQ-NF-002 | цей звіт |
| REQ-NF-003 | запуск набору однією командою — tools/run_tests.py |
| REQ-NF-004 | порядок комітів test: і feat: — історія Git |
| REQ-NF-006 | записи сесій роботи з агентом — logs/agent-session-03.md |
| REQ-NF-007 | позначка [agent] у повідомленнях комітів |
| REQ-NF-011 | запис у базу в момент підтвердження — транзакції SQLite |
| REQ-NF-013 | стек Python, FastAPI, SQLite |
| REQ-NF-015 | розміщення коду в /src і тестів у /tests |

## Поза обсягом ЛР5

| Вимога | Зміст |
|---|---|
| REQ-NF-012 | файли перекладів для української та англійської |
| REQ-NF-014 | побудова графіків бібліотекою Chart.js у браузері |
| REQ-I-001 | вебсторінка з формою, списком і графіком |
| REQ-I-002 | вибір активного профілю в інтерфейсі |
| REQ-I-004 | формати дати й часу в інтерфейсі |
