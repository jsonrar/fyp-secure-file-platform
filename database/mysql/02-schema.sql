-- MySQL 8.4 empty-database schema installation.
--
-- Run this file exactly once as MySQL root/administrator, immediately after
-- 01-provision.sql. From the repository root on the database server:
--
--     sudo mysql < database/mysql/02-schema.sql
--     mysql --user=root --password < database/mysql/02-schema.sql
--
-- Never put the root password directly on the command line, never use an
-- interactive SOURCE command, and never use the mysql client's --force option.
-- For a remote application connection, use protected copies of all three SQL
-- files and replace every localhost account-host literal consistently in each
-- copy. Keep the environment-specific copies out of version control.
--
-- This script is deliberately non-idempotent and accepts only a completely
-- empty fyp_secure_file_platform schema. MySQL DDL is not fully transactional.
-- If any statement fails, do not rerun this file over the partial schema:
-- diagnose the failure, recreate the disposable empty database or restore the
-- verified pre-deployment backup, then restart from 01-provision.sql.
--
-- The DDL below is the flattened final state represented by revisions
-- 0001_initial and 0002_auth_identity_sessions. Production deployment does not
-- run Alembic. The alembic_version row is retained only as a compatibility
-- marker for development tooling and must be updated together with reviewed
-- future root-executed SQL release scripts.

USE `fyp_secure_file_platform`;
SET SESSION time_zone = '+00:00';

-- Fail closed before permanent DDL unless this is Oracle MySQL 8.4 in strict
-- mode, the database encoding is exact, and no persistent schema object exists.
CREATE TEMPORARY TABLE fyp_schema_install_guard (
    preflight_ok TINYINT NOT NULL,
    CONSTRAINT ck_fyp_schema_install_preflight CHECK (preflight_ok = 1)
) ENGINE=InnoDB;

INSERT INTO fyp_schema_install_guard (preflight_ok)
SELECT CASE
    WHEN SUBSTRING_INDEX(VERSION(), '.', 2) = '8.4'
     AND LOWER(CONCAT(VERSION(), ' ', @@version_comment)) NOT LIKE '%mariadb%'
     AND (
         FIND_IN_SET('STRICT_TRANS_TABLES', @@SESSION.sql_mode) > 0
         OR FIND_IN_SET('STRICT_ALL_TABLES', @@SESSION.sql_mode) > 0
     )
     AND (
         SELECT COUNT(*)
         FROM information_schema.SCHEMATA
         WHERE SCHEMA_NAME = DATABASE()
           AND DEFAULT_CHARACTER_SET_NAME = 'utf8mb4'
           AND DEFAULT_COLLATION_NAME = 'utf8mb4_unicode_ci'
     ) = 1
     AND (
         SELECT COUNT(*)
         FROM information_schema.TABLES
         WHERE TABLE_SCHEMA = DATABASE()
     ) = 0
     AND (
         SELECT COUNT(*)
         FROM information_schema.ROUTINES
         WHERE ROUTINE_SCHEMA = DATABASE()
     ) = 0
     AND (
         SELECT COUNT(*)
         FROM information_schema.TRIGGERS
         WHERE TRIGGER_SCHEMA = DATABASE()
     ) = 0
     AND (
         SELECT COUNT(*)
         FROM information_schema.EVENTS
         WHERE EVENT_SCHEMA = DATABASE()
     ) = 0
    THEN 1
    ELSE 0
END;

DROP TEMPORARY TABLE fyp_schema_install_guard;

CREATE TABLE auth_login_throttles (
    scope ENUM(
        'ACCOUNT',
        'IP',
        'REAUTH_ACCOUNT',
        'REAUTH_IP',
        'REGISTRATION_IP'
    ) NOT NULL,
    key_hash CHAR(64) NOT NULL,
    failed_count INTEGER UNSIGNED NOT NULL DEFAULT '0',
    window_started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    blocked_until DATETIME,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (scope, key_hash)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_auth_login_throttles_blocked_until
    ON auth_login_throttles (blocked_until);
CREATE INDEX idx_auth_login_throttles_updated_at
    ON auth_login_throttles (updated_at);

CREATE TABLE recovery_keys (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    public_key_pem TEXT NOT NULL,
    algorithm VARCHAR(50) NOT NULL DEFAULT 'RSA-OAEP-SHA256',
    fingerprint CHAR(64) NOT NULL,
    status ENUM('ACTIVE', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at DATETIME,
    PRIMARY KEY (id),
    CONSTRAINT uq_recovery_keys_fingerprint UNIQUE (fingerprint)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_recovery_keys_created_at ON recovery_keys (created_at);
CREATE INDEX idx_recovery_keys_status ON recovery_keys (status);

CREATE TABLE users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_uuid CHAR(36) NOT NULL,
    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    `role` ENUM('USER', 'ADMIN', 'RECOVERY_OFFICER') NOT NULL DEFAULT 'USER',
    status ENUM('ACTIVE', 'DISABLED', 'DELETED') NOT NULL DEFAULT 'ACTIVE',
    email_verified BOOL NOT NULL DEFAULT '0',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    password_changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login_at DATETIME,
    PRIMARY KEY (id),
    CONSTRAINT uq_users_user_uuid UNIQUE (user_uuid),
    CONSTRAINT uq_users_username UNIQUE (username),
    CONSTRAINT uq_users_email UNIQUE (email)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_users_created_at ON users (created_at);
CREATE INDEX idx_users_role ON users (`role`);
CREATE INDEX idx_users_status ON users (status);

CREATE TABLE audit_logs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    actor_user_id BIGINT UNSIGNED,
    action VARCHAR(100) NOT NULL,
    resource_type ENUM(
        'AUTH',
        'USER',
        'FILE',
        'SHARE',
        'RECOVERY',
        'INTEGRITY',
        'SYSTEM'
    ) NOT NULL,
    resource_id VARCHAR(100),
    target_user_id BIGINT UNSIGNED,
    result ENUM('SUCCESS', 'FAIL') NOT NULL,
    ip_address VARCHAR(45),
    user_agent TEXT,
    description TEXT,
    metadata_json JSON NOT NULL,
    previous_hash CHAR(64),
    current_hash CHAR(64) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    CONSTRAINT fk_audit_logs_actor_user
        FOREIGN KEY (actor_user_id) REFERENCES users (id)
        ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_audit_logs_target_user
        FOREIGN KEY (target_user_id) REFERENCES users (id)
        ON DELETE RESTRICT ON UPDATE RESTRICT
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_audit_logs_action ON audit_logs (action);
CREATE INDEX idx_audit_logs_actor_user_id ON audit_logs (actor_user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs (created_at);
CREATE INDEX idx_audit_logs_resource ON audit_logs (resource_type, resource_id);
CREATE INDEX idx_audit_logs_result ON audit_logs (result);
CREATE INDEX idx_audit_logs_target_user_id ON audit_logs (target_user_id);

CREATE TABLE files (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    file_uuid CHAR(36) NOT NULL,
    owner_id BIGINT UNSIGNED NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    storage_object_key VARCHAR(500) NOT NULL,
    mime_type VARCHAR(150),
    file_size_bytes BIGINT UNSIGNED NOT NULL,
    encrypted_size_bytes BIGINT UNSIGNED,
    encryption_algorithm VARCHAR(50) NOT NULL DEFAULT 'AES-256-GCM',
    iv VARBINARY(32) NOT NULL,
    auth_tag VARBINARY(32) NOT NULL,
    encrypted_sha256 CHAR(64) NOT NULL,
    status ENUM('ACTIVE', 'DELETED', 'CORRUPTED') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at DATETIME,
    PRIMARY KEY (id),
    CONSTRAINT uq_files_file_uuid UNIQUE (file_uuid),
    CONSTRAINT uq_files_stored_filename UNIQUE (stored_filename),
    CONSTRAINT fk_files_owner
        FOREIGN KEY (owner_id) REFERENCES users (id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_files_created_at ON files (created_at);
CREATE INDEX idx_files_owner_id ON files (owner_id);
CREATE INDEX idx_files_status ON files (status);

CREATE TABLE user_keys (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    user_id BIGINT UNSIGNED NOT NULL,
    public_key_pem TEXT NOT NULL,
    algorithm VARCHAR(50) NOT NULL DEFAULT 'RSA-OAEP-SHA256',
    fingerprint CHAR(64) NOT NULL,
    status ENUM('ACTIVE', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at DATETIME,
    PRIMARY KEY (id),
    CONSTRAINT uq_user_keys_fingerprint UNIQUE (fingerprint),
    CONSTRAINT fk_user_keys_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_user_keys_created_at ON user_keys (created_at);
CREATE INDEX idx_user_keys_status ON user_keys (status);
CREATE INDEX idx_user_keys_user_id ON user_keys (user_id);

CREATE TABLE user_sessions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    session_uuid CHAR(36) NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    access_token_hash CHAR(64) NOT NULL,
    status ENUM('ACTIVE', 'EXPIRED', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    access_expires_at DATETIME NOT NULL,
    absolute_expires_at DATETIME NOT NULL,
    revoked_at DATETIME,
    revoked_reason VARCHAR(100),
    PRIMARY KEY (id),
    CONSTRAINT uq_user_sessions_session_uuid UNIQUE (session_uuid),
    CONSTRAINT uq_user_sessions_access_token_hash UNIQUE (access_token_hash),
    CONSTRAINT ck_user_sessions_access_before_absolute
        CHECK (access_expires_at <= absolute_expires_at),
    CONSTRAINT fk_user_sessions_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_user_sessions_created_at ON user_sessions (created_at);
CREATE INDEX idx_user_sessions_status_access_expires
    ON user_sessions (status, access_expires_at);
CREATE INDEX idx_user_sessions_status_absolute_expires
    ON user_sessions (status, absolute_expires_at);
CREATE INDEX idx_user_sessions_user_status
    ON user_sessions (user_id, status);

CREATE TABLE audit_chain_heads (
    id TINYINT UNSIGNED NOT NULL,
    last_log_id BIGINT UNSIGNED,
    current_hash CHAR(64) NOT NULL,
    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    PRIMARY KEY (id),
    CONSTRAINT ck_audit_chain_heads_singleton CHECK (id = 1),
    CONSTRAINT fk_audit_chain_heads_last_log
        FOREIGN KEY (last_log_id) REFERENCES audit_logs (id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE TABLE file_access_grants (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    file_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    granted_by BIGINT UNSIGNED NOT NULL,
    can_download BOOL NOT NULL DEFAULT '1',
    can_share BOOL NOT NULL DEFAULT '0',
    can_revoke BOOL NOT NULL DEFAULT '0',
    can_manage BOOL NOT NULL DEFAULT '0',
    status ENUM('ACTIVE', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at DATETIME,
    PRIMARY KEY (id),
    CONSTRAINT uq_file_access_grants_file_user UNIQUE (file_id, user_id),
    CONSTRAINT fk_file_access_grants_file
        FOREIGN KEY (file_id) REFERENCES files (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_file_access_grants_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_file_access_grants_granted_by
        FOREIGN KEY (granted_by) REFERENCES users (id)
        ON DELETE RESTRICT ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_file_access_grants_created_at
    ON file_access_grants (created_at);
CREATE INDEX idx_file_access_grants_file_id
    ON file_access_grants (file_id);
CREATE INDEX idx_file_access_grants_granted_by
    ON file_access_grants (granted_by);
CREATE INDEX idx_file_access_grants_status
    ON file_access_grants (status);
CREATE INDEX idx_file_access_grants_user_id
    ON file_access_grants (user_id);

CREATE TABLE file_key_wrappings (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    file_id BIGINT UNSIGNED NOT NULL,
    recipient_type ENUM('USER', 'RECOVERY') NOT NULL,
    recipient_user_id BIGINT UNSIGNED,
    user_key_id BIGINT UNSIGNED,
    recovery_key_id BIGINT UNSIGNED,
    wrapped_file_key VARBINARY(1024) NOT NULL,
    wrapping_algorithm VARCHAR(50) NOT NULL DEFAULT 'RSA-OAEP-SHA256',
    status ENUM('ACTIVE', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at DATETIME,
    PRIMARY KEY (id),
    CONSTRAINT fk_file_key_wrappings_file
        FOREIGN KEY (file_id) REFERENCES files (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_file_key_wrappings_recipient_user
        FOREIGN KEY (recipient_user_id) REFERENCES users (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_file_key_wrappings_user_key
        FOREIGN KEY (user_key_id) REFERENCES user_keys (id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT fk_file_key_wrappings_recovery_key
        FOREIGN KEY (recovery_key_id) REFERENCES recovery_keys (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_file_key_wrappings_created_at
    ON file_key_wrappings (created_at);
CREATE INDEX idx_file_key_wrappings_file_id
    ON file_key_wrappings (file_id);
CREATE INDEX idx_file_key_wrappings_recipient_type
    ON file_key_wrappings (recipient_type);
CREATE INDEX idx_file_key_wrappings_recipient_user_id
    ON file_key_wrappings (recipient_user_id);
CREATE INDEX idx_file_key_wrappings_recovery_key_id
    ON file_key_wrappings (recovery_key_id);
CREATE INDEX idx_file_key_wrappings_status
    ON file_key_wrappings (status);
CREATE INDEX idx_file_key_wrappings_user_key_id
    ON file_key_wrappings (user_key_id);

CREATE TABLE integrity_checks (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    file_id BIGINT UNSIGNED NOT NULL,
    checked_by BIGINT UNSIGNED,
    expected_hash CHAR(64) NOT NULL,
    actual_hash CHAR(64),
    result ENUM('VALID', 'MODIFIED', 'MISSING', 'ERROR') NOT NULL,
    message TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_integrity_checks_file
        FOREIGN KEY (file_id) REFERENCES files (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_integrity_checks_checked_by
        FOREIGN KEY (checked_by) REFERENCES users (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_integrity_checks_checked_by
    ON integrity_checks (checked_by);
CREATE INDEX idx_integrity_checks_created_at
    ON integrity_checks (created_at);
CREATE INDEX idx_integrity_checks_file_id
    ON integrity_checks (file_id);
CREATE INDEX idx_integrity_checks_result
    ON integrity_checks (result);

CREATE TABLE recovery_requests (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    request_uuid CHAR(36) NOT NULL,
    file_id BIGINT UNSIGNED NOT NULL,
    requested_by BIGINT UNSIGNED NOT NULL,
    approved_by BIGINT UNSIGNED,
    reason TEXT NOT NULL,
    rejection_reason TEXT,
    status ENUM(
        'PENDING',
        'APPROVED',
        'REJECTED',
        'EXECUTED',
        'CANCELLED'
    ) NOT NULL DEFAULT 'PENDING',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_at DATETIME,
    rejected_at DATETIME,
    executed_at DATETIME,
    PRIMARY KEY (id),
    CONSTRAINT uq_recovery_requests_request_uuid UNIQUE (request_uuid),
    CONSTRAINT fk_recovery_requests_file
        FOREIGN KEY (file_id) REFERENCES files (id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_recovery_requests_requested_by
        FOREIGN KEY (requested_by) REFERENCES users (id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_recovery_requests_approved_by
        FOREIGN KEY (approved_by) REFERENCES users (id)
        ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_recovery_requests_approved_by
    ON recovery_requests (approved_by);
CREATE INDEX idx_recovery_requests_created_at
    ON recovery_requests (created_at);
CREATE INDEX idx_recovery_requests_file_id
    ON recovery_requests (file_id);
CREATE INDEX idx_recovery_requests_requested_by
    ON recovery_requests (requested_by);
CREATE INDEX idx_recovery_requests_status
    ON recovery_requests (status);

CREATE TABLE session_refresh_tokens (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    session_id BIGINT UNSIGNED NOT NULL,
    token_hash CHAR(64) NOT NULL,
    generation INTEGER UNSIGNED NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    consumed_at DATETIME,
    revoked_at DATETIME,
    PRIMARY KEY (id),
    CONSTRAINT uq_session_refresh_tokens_token_hash UNIQUE (token_hash),
    CONSTRAINT uq_session_refresh_tokens_session_generation
        UNIQUE (session_id, generation),
    CONSTRAINT ck_session_refresh_tokens_expiry_after_creation
        CHECK (expires_at > created_at),
    CONSTRAINT fk_session_refresh_tokens_session
        FOREIGN KEY (session_id) REFERENCES user_sessions (id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

CREATE INDEX idx_session_refresh_tokens_expires_at
    ON session_refresh_tokens (expires_at);

-- Seed the only application bootstrap row.
INSERT INTO audit_chain_heads (id, last_log_id, current_hash)
VALUES (
    1,
    NULL,
    '0000000000000000000000000000000000000000000000000000000000000000'
);

-- Grant the runtime identity CRUD only on ordinary application state. Audit
-- events remain append-only, the chain head can only be read/advanced, and the
-- schema compatibility marker is never exposed to the application identity.
GRANT SELECT, INSERT, UPDATE, DELETE
    ON `fyp_secure_file_platform`.`auth_login_throttles`
    TO 'fyp_user'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE
    ON `fyp_secure_file_platform`.`recovery_keys`
    TO 'fyp_user'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE
    ON `fyp_secure_file_platform`.`users`
    TO 'fyp_user'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE
    ON `fyp_secure_file_platform`.`files`
    TO 'fyp_user'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE
    ON `fyp_secure_file_platform`.`user_keys`
    TO 'fyp_user'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE
    ON `fyp_secure_file_platform`.`user_sessions`
    TO 'fyp_user'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE
    ON `fyp_secure_file_platform`.`file_access_grants`
    TO 'fyp_user'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE
    ON `fyp_secure_file_platform`.`file_key_wrappings`
    TO 'fyp_user'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE
    ON `fyp_secure_file_platform`.`integrity_checks`
    TO 'fyp_user'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE
    ON `fyp_secure_file_platform`.`recovery_requests`
    TO 'fyp_user'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE
    ON `fyp_secure_file_platform`.`session_refresh_tokens`
    TO 'fyp_user'@'localhost';
GRANT SELECT, INSERT
    ON `fyp_secure_file_platform`.`audit_logs`
    TO 'fyp_user'@'localhost';
GRANT SELECT, UPDATE
    ON `fyp_secure_file_platform`.`audit_chain_heads`
    TO 'fyp_user'@'localhost';

-- Create the compatibility table and marker last. Their presence at the
-- expected value proves every preceding batch statement completed.
CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
) ENGINE=InnoDB
  DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

INSERT INTO alembic_version (version_num)
VALUES ('0002_auth_identity_sessions');
