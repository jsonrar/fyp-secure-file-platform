-- Non-destructive development bootstrap only.
--
-- Application tables, indexes, and constraints are owned by the SQLAlchemy
-- models and Alembic migrations under backend/migrations. After provisioning
-- the database, run `alembic upgrade head` from the backend directory.
--
-- Docker Compose already creates this database through MYSQL_DATABASE. This
-- statement is retained only for developers who provision MySQL manually.

CREATE DATABASE IF NOT EXISTS fyp_secure_file_platform
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;
