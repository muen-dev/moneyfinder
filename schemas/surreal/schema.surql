-- MoneyFinder SurrealDB schema
-- Namespace: moneyfinder  Database: main
-- All timestamps are UTC datetime

DEFINE NAMESPACE IF NOT EXISTS moneyfinder;
DEFINE DATABASE IF NOT EXISTS main;

USE NS moneyfinder DB main;

DEFINE TABLE business SCHEMAFULL;
DEFINE FIELD legal_name ON business TYPE string;
DEFINE FIELD dbas ON business TYPE array<string> DEFAULT [];
DEFINE FIELD business_type ON business TYPE option<string>;
DEFINE FIELD addresses ON business TYPE array<object> DEFAULT [];
DEFINE FIELD authorized_representative ON business TYPE option<object>;
DEFINE FIELD search_consent ON business TYPE bool DEFAULT false;
DEFINE FIELD created_at ON business TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON business TYPE datetime DEFAULT time::now();

DEFINE TABLE fact SCHEMAFULL;
DEFINE FIELD business ON fact TYPE record<business>;
DEFINE FIELD key ON fact TYPE string;
DEFINE FIELD value ON fact TYPE string;
DEFINE FIELD source ON fact TYPE string;
DEFINE FIELD confidence ON fact TYPE float DEFAULT 1.0;
DEFINE FIELD captured_at ON fact TYPE datetime DEFAULT time::now();

DEFINE TABLE claim SCHEMAFULL;
DEFINE FIELD business ON claim TYPE record<business>;
DEFINE FIELD match_name ON claim TYPE string;
DEFINE FIELD property_type ON claim TYPE option<string>;
DEFINE FIELD city ON claim TYPE option<string>;
DEFINE FIELD zip ON claim TYPE option<string>;
DEFINE FIELD amount_cents ON claim TYPE option<int>;
DEFINE FIELD amount_type ON claim TYPE string DEFAULT "matched_estimate";
DEFINE FIELD confidence ON claim TYPE float;
DEFINE FIELD status ON claim TYPE string DEFAULT "MATCH_FOUND";
DEFINE FIELD confirmation_id ON claim TYPE option<string>;
DEFINE FIELD form_hash ON claim TYPE option<string>;
DEFINE FIELD created_at ON claim TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON claim TYPE datetime DEFAULT time::now();
DEFINE FIELD submitted_at ON claim TYPE option<datetime>;
DEFINE FIELD approved_at ON claim TYPE option<datetime>;
DEFINE FIELD payment_issued_at ON claim TYPE option<datetime>;
DEFINE FIELD payment_confirmed_at ON claim TYPE option<datetime>;
DEFINE FIELD last_checked_at ON claim TYPE option<datetime>;
DEFINE FIELD expected_by ON claim TYPE option<datetime>;

DEFINE TABLE form_field SCHEMAFULL;
DEFINE FIELD claim ON form_field TYPE record<claim>;
DEFINE FIELD field ON form_field TYPE string;
DEFINE FIELD value ON form_field TYPE string;
DEFINE FIELD source ON form_field TYPE string;
DEFINE FIELD confidence ON form_field TYPE float DEFAULT 1.0;
DEFINE FIELD requires_confirmation ON form_field TYPE bool DEFAULT false;
DEFINE FIELD conflicting_value ON form_field TYPE option<string>;
DEFINE FIELD source_of_conflict ON form_field TYPE option<string>;
DEFINE FIELD edited_by_user ON form_field TYPE bool DEFAULT false;
DEFINE FIELD updated_at ON form_field TYPE datetime DEFAULT time::now();

DEFINE TABLE pipeline_event SCHEMAFULL;
DEFINE FIELD claim ON pipeline_event TYPE record<claim>;
DEFINE FIELD from_status ON pipeline_event TYPE option<string>;
DEFINE FIELD to_status ON pipeline_event TYPE string;
DEFINE FIELD actor ON pipeline_event TYPE string;
DEFINE FIELD evidence ON pipeline_event TYPE option<record<evidence>>;
DEFINE FIELD note ON pipeline_event TYPE option<string>;
DEFINE FIELD created_at ON pipeline_event TYPE datetime DEFAULT time::now();

DEFINE TABLE evidence SCHEMAFULL;
DEFINE FIELD claim ON evidence TYPE record<claim>;
DEFINE FIELD kind ON evidence TYPE string;
DEFINE FIELD source ON evidence TYPE string;
DEFINE FIELD reference ON evidence TYPE option<string>;
DEFINE FIELD payload ON evidence TYPE option<object>;
DEFINE FIELD created_at ON evidence TYPE datetime DEFAULT time::now();

DEFINE TABLE eval_trace SCHEMAFULL;
DEFINE FIELD claim ON eval_trace TYPE option<record<claim>>;
DEFINE FIELD suite ON eval_trace TYPE string;
DEFINE FIELD metric ON eval_trace TYPE string;
DEFINE FIELD score ON eval_trace TYPE float;
DEFINE FIELD details ON eval_trace TYPE option<object>;
DEFINE FIELD created_at ON eval_trace TYPE datetime DEFAULT time::now();

-- Immutable-ish event append helper pattern:
-- CREATE pipeline_event SET claim = $c, from_status = $from, to_status = $to,
--   actor = $actor, evidence = $e, created_at = time::now();
