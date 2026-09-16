-- Rollback for 012_learning_audit_log.
DROP TABLE IF EXISTS learning_audit_log;
DELETE FROM app_schema_migrations WHERE version = '012_learning_audit_log';
