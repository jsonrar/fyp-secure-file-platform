-- =========================================================
-- FYP Secure File Encryption & Sharing Platform
-- Database Initialization Script
-- Target DBMS: MySQL 8.x
-- Database: fyp_secure_file_platform
-- =========================================================

CREATE DATABASE IF NOT EXISTS fyp_secure_file_platform
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE fyp_secure_file_platform;

-- =========================================================
-- Drop existing tables for development reset
-- =========================================================
-- 注意：在生产环境中请勿执行 DROP TABLE 操作！此处仅用于开发阶段快速重置数据库。

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS recovery_requests;
DROP TABLE IF EXISTS integrity_checks;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS file_access_grants;
DROP TABLE IF EXISTS file_key_wrappings;
DROP TABLE IF EXISTS files;
DROP TABLE IF EXISTS recovery_keys;
DROP TABLE IF EXISTS user_sessions;
DROP TABLE IF EXISTS user_keys;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

-- =========================================================
-- 1. Users
-- Register form:
-- username + email + password + confirm password
-- Password confirmation is handled in backend, not database.
-- =========================================================

CREATE TABLE users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    username VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    role ENUM('USER', 'ADMIN', 'RECOVERY_OFFICER') NOT NULL DEFAULT 'USER',
    status ENUM('ACTIVE', 'DISABLED', 'DELETED') NOT NULL DEFAULT 'ACTIVE',

    email_verified BOOLEAN NOT NULL DEFAULT FALSE,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login_at DATETIME NULL,

    PRIMARY KEY (id),

    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_email (email),

    KEY idx_users_role (role),
    KEY idx_users_status (status),
    KEY idx_users_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 2. User Public Keys
-- Private keys are NOT stored in database.
-- Users keep their private keys locally.
-- =========================================================

CREATE TABLE user_keys (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    user_id BIGINT UNSIGNED NOT NULL,

    public_key_pem TEXT NOT NULL,
    algorithm VARCHAR(50) NOT NULL DEFAULT 'RSA-OAEP-SHA256',
    fingerprint CHAR(64) NOT NULL,

    status ENUM('ACTIVE', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at DATETIME NULL,

    PRIMARY KEY (id),

    UNIQUE KEY uq_user_keys_fingerprint (fingerprint),

    KEY idx_user_keys_user_id (user_id),
    KEY idx_user_keys_status (status),
    KEY idx_user_keys_created_at (created_at),

    CONSTRAINT fk_user_keys_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 3. User Sessions
-- Store hashed session tokens, not raw tokens.
-- =========================================================

CREATE TABLE user_sessions (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    user_id BIGINT UNSIGNED NOT NULL,
    session_token_hash CHAR(64) NOT NULL,

    status ENUM('ACTIVE', 'EXPIRED', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',

    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    revoked_at DATETIME NULL,

    PRIMARY KEY (id),

    UNIQUE KEY uq_user_sessions_token_hash (session_token_hash),

    KEY idx_user_sessions_user_id (user_id),
    KEY idx_user_sessions_status (status),
    KEY idx_user_sessions_expires_at (expires_at),
    KEY idx_user_sessions_created_at (created_at),

    CONSTRAINT fk_user_sessions_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 4. Recovery Keys
-- Recovery private keys are NOT stored in database.
-- Only recovery public keys are stored.
-- =========================================================

CREATE TABLE recovery_keys (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    public_key_pem TEXT NOT NULL,
    algorithm VARCHAR(50) NOT NULL DEFAULT 'RSA-OAEP-SHA256',
    fingerprint CHAR(64) NOT NULL,

    status ENUM('ACTIVE', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at DATETIME NULL,

    PRIMARY KEY (id),

    UNIQUE KEY uq_recovery_keys_fingerprint (fingerprint),

    KEY idx_recovery_keys_status (status),
    KEY idx_recovery_keys_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 5. Files
-- Store file metadata and encryption metadata only.
-- Plaintext files are not stored permanently.
-- =========================================================

CREATE TABLE files (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    file_uuid CHAR(36) NOT NULL,
    owner_id BIGINT UNSIGNED NOT NULL,

    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,

    mime_type VARCHAR(150) NULL,

    file_size_bytes BIGINT UNSIGNED NOT NULL,
    encrypted_size_bytes BIGINT UNSIGNED NULL,

    encryption_algorithm VARCHAR(50) NOT NULL DEFAULT 'AES-256-GCM',

    iv VARBINARY(32) NOT NULL,
    auth_tag VARBINARY(32) NOT NULL,

    encrypted_sha256 CHAR(64) NOT NULL,

    status ENUM('ACTIVE', 'DELETED', 'CORRUPTED') NOT NULL DEFAULT 'ACTIVE',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,

    PRIMARY KEY (id),

    UNIQUE KEY uq_files_file_uuid (file_uuid),
    UNIQUE KEY uq_files_stored_filename (stored_filename),

    KEY idx_files_owner_id (owner_id),
    KEY idx_files_status (status),
    KEY idx_files_created_at (created_at),

    CONSTRAINT fk_files_owner
        FOREIGN KEY (owner_id)
        REFERENCES users(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 6. File Key Wrappings
-- Stores AES file keys encrypted using user or recovery public keys.
--
-- Important:
-- The recipient consistency rule is enforced in backend service logic.
--
-- USER wrapping:
-- recipient_type = 'USER'
-- recipient_user_id IS NOT NULL
-- user_key_id IS NOT NULL
-- recovery_key_id IS NULL
--
-- RECOVERY wrapping:
-- recipient_type = 'RECOVERY'
-- recipient_user_id IS NULL
-- user_key_id IS NULL
-- recovery_key_id IS NOT NULL
--
-- We do not use a CHECK constraint here because MySQL may reject CHECK
-- constraints that reference columns also involved in FK referential actions.
-- =========================================================

CREATE TABLE file_key_wrappings (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    file_id BIGINT UNSIGNED NOT NULL,

    recipient_type ENUM('USER', 'RECOVERY') NOT NULL,

    recipient_user_id BIGINT UNSIGNED NULL,
    user_key_id BIGINT UNSIGNED NULL,
    recovery_key_id BIGINT UNSIGNED NULL,

    wrapped_file_key VARBINARY(1024) NOT NULL,
    wrapping_algorithm VARCHAR(50) NOT NULL DEFAULT 'RSA-OAEP-SHA256',

    status ENUM('ACTIVE', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at DATETIME NULL,

    PRIMARY KEY (id),

    KEY idx_file_key_wrappings_file_id (file_id),
    KEY idx_file_key_wrappings_recipient_type (recipient_type),
    KEY idx_file_key_wrappings_recipient_user_id (recipient_user_id),
    KEY idx_file_key_wrappings_user_key_id (user_key_id),
    KEY idx_file_key_wrappings_recovery_key_id (recovery_key_id),
    KEY idx_file_key_wrappings_status (status),
    KEY idx_file_key_wrappings_created_at (created_at),

    CONSTRAINT fk_file_key_wrappings_file
        FOREIGN KEY (file_id)
        REFERENCES files(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_file_key_wrappings_recipient_user
        FOREIGN KEY (recipient_user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_file_key_wrappings_user_key
        FOREIGN KEY (user_key_id)
        REFERENCES user_keys(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT fk_file_key_wrappings_recovery_key
        FOREIGN KEY (recovery_key_id)
        REFERENCES recovery_keys(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 7. File Access Grants
-- Represents logical permission access.
--
-- file_access_grants = permission access
-- file_key_wrappings = cryptographic access
--
-- Download should require both:
-- 1. ACTIVE file_access_grants
-- 2. ACTIVE file_key_wrappings
-- =========================================================

CREATE TABLE file_access_grants (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    file_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    granted_by BIGINT UNSIGNED NOT NULL,

    permission_level ENUM('OWNER', 'VIEWER', 'EDITOR') NOT NULL DEFAULT 'VIEWER',

    can_download BOOLEAN NOT NULL DEFAULT TRUE,
    can_share BOOLEAN NOT NULL DEFAULT FALSE,
    can_revoke BOOLEAN NOT NULL DEFAULT FALSE,
    can_manage BOOLEAN NOT NULL DEFAULT FALSE,

    status ENUM('ACTIVE', 'REVOKED') NOT NULL DEFAULT 'ACTIVE',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at DATETIME NULL,

    PRIMARY KEY (id),

    UNIQUE KEY uq_file_access_grants_file_user (file_id, user_id),

    KEY idx_file_access_grants_file_id (file_id),
    KEY idx_file_access_grants_user_id (user_id),
    KEY idx_file_access_grants_granted_by (granted_by),
    KEY idx_file_access_grants_status (status),
    KEY idx_file_access_grants_created_at (created_at),

    CONSTRAINT fk_file_access_grants_file
        FOREIGN KEY (file_id)
        REFERENCES files(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_file_access_grants_user
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_file_access_grants_granted_by
        FOREIGN KEY (granted_by)
        REFERENCES users(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 8. Audit Logs
-- Stores security-sensitive operations.
--
-- Hash chain:
-- current_hash = SHA256(previous_hash + log_content)
--
-- For the first log, previous_hash can be NULL.
-- =========================================================

CREATE TABLE audit_logs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    actor_user_id BIGINT UNSIGNED NULL,

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

    resource_id VARCHAR(100) NULL,

    target_user_id BIGINT UNSIGNED NULL,

    result ENUM('SUCCESS', 'FAIL') NOT NULL,

    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,

    description TEXT NULL,
    metadata_json JSON NULL,

    previous_hash CHAR(64) NULL,
    current_hash CHAR(64) NOT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    KEY idx_audit_logs_actor_user_id (actor_user_id),
    KEY idx_audit_logs_target_user_id (target_user_id),
    KEY idx_audit_logs_action (action),
    KEY idx_audit_logs_resource (resource_type, resource_id),
    KEY idx_audit_logs_result (result),
    KEY idx_audit_logs_created_at (created_at),

    CONSTRAINT fk_audit_logs_actor_user
        FOREIGN KEY (actor_user_id)
        REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,

    CONSTRAINT fk_audit_logs_target_user
        FOREIGN KEY (target_user_id)
        REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 9. Integrity Checks
-- Stores integrity verification history.
-- =========================================================

CREATE TABLE integrity_checks (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    file_id BIGINT UNSIGNED NOT NULL,
    checked_by BIGINT UNSIGNED NULL,

    expected_hash CHAR(64) NOT NULL,
    actual_hash CHAR(64) NULL,

    result ENUM('VALID', 'MODIFIED', 'MISSING', 'ERROR') NOT NULL,

    message TEXT NULL,

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (id),

    KEY idx_integrity_checks_file_id (file_id),
    KEY idx_integrity_checks_checked_by (checked_by),
    KEY idx_integrity_checks_result (result),
    KEY idx_integrity_checks_created_at (created_at),

    CONSTRAINT fk_integrity_checks_file
        FOREIGN KEY (file_id)
        REFERENCES files(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_integrity_checks_checked_by
        FOREIGN KEY (checked_by)
        REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- 10. Recovery Requests
-- Stores recovery workflow records.
-- =========================================================

CREATE TABLE recovery_requests (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,

    request_uuid CHAR(36) NOT NULL,

    file_id BIGINT UNSIGNED NOT NULL,

    requested_by BIGINT UNSIGNED NOT NULL,
    approved_by BIGINT UNSIGNED NULL,

    reason TEXT NOT NULL,
    rejection_reason TEXT NULL,

    status ENUM(
        'PENDING',
        'APPROVED',
        'REJECTED',
        'EXECUTED',
        'CANCELLED'
    ) NOT NULL DEFAULT 'PENDING',

    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    approved_at DATETIME NULL,
    rejected_at DATETIME NULL,
    executed_at DATETIME NULL,

    PRIMARY KEY (id),

    UNIQUE KEY uq_recovery_requests_request_uuid (request_uuid),

    KEY idx_recovery_requests_file_id (file_id),
    KEY idx_recovery_requests_requested_by (requested_by),
    KEY idx_recovery_requests_approved_by (approved_by),
    KEY idx_recovery_requests_status (status),
    KEY idx_recovery_requests_created_at (created_at),

    CONSTRAINT fk_recovery_requests_file
        FOREIGN KEY (file_id)
        REFERENCES files(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,

    CONSTRAINT fk_recovery_requests_requested_by
        FOREIGN KEY (requested_by)
        REFERENCES users(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,

    CONSTRAINT fk_recovery_requests_approved_by
        FOREIGN KEY (approved_by)
        REFERENCES users(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =========================================================
-- Optional Development Database User
--
-- Run this script using root or another MySQL admin account.
-- This user should match the backend .env file:
--
-- DB_USER=fyp_user
-- DB_PASSWORD=fyp_password
-- DB_NAME=fyp_secure_file_platform
-- =========================================================

CREATE USER IF NOT EXISTS 'fyp_user'@'localhost'
IDENTIFIED BY 'fyp_password';

GRANT ALL PRIVILEGES
ON fyp_secure_file_platform.*
TO 'fyp_user'@'localhost';

FLUSH PRIVILEGES;

-- =========================================================
-- End of init.sql
-- =========================================================