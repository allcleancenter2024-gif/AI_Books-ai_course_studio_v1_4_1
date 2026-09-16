-- Rollback for 011_learning_tools.
-- Execute only after disabling the feature and confirming no dependent data is needed.
DROP TABLE IF EXISTS course_versions;
DROP TABLE IF EXISTS course_update_decisions;
DROP TABLE IF EXISTS course_update_suggestions;
DROP TABLE IF EXISTS course_update_matches;
DROP TABLE IF EXISTS course_tool_references;
DROP TABLE IF EXISTS update_rules;
DROP TABLE IF EXISTS source_evidence;
DROP TABLE IF EXISTS update_events;
DROP TABLE IF EXISTS modern_prompt_examples;
DROP TABLE IF EXISTS prompt_examples;
DROP TABLE IF EXISTS prompt_skills;
DROP TABLE IF EXISTS prompt_frameworks;
DROP TABLE IF EXISTS timeline_events;
DROP TABLE IF EXISTS tool_capabilities;
DROP TABLE IF EXISTS tool_versions;
DROP TABLE IF EXISTS learning_tools;
DELETE FROM app_schema_migrations WHERE version = '011_learning_tools';
