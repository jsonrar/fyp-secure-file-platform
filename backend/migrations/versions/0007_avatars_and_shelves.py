"""Add optional account avatars and owner-scoped file shelves.

Revision ID: 0007_avatars_and_shelves
Revises: 0006_chacha20_poly1305
Create Date: 2026-09-27

Two product features that share a revision because both are plain metadata and neither
touches the cryptographic envelope.

Avatars are the first deliberately *unencrypted* user content in the schema. A profile
picture is shown to whoever can already see the profile, so encrypting it would buy nothing
and cost the account key. The columns record which stored object belongs to the account and
what it is, so a response never has to sniff the bytes or trust the object's name to decide
the Content-Type it serves; the CHECK keeps the description whole and bounded, because a row
that names an object but not its type would be served as something the server never
verified.

Shelves are organisation, not access control. A shelf belongs to one owner, holds no key
material, and is invisible to anyone a file inside it was shared with -- so `files.shelf_id`
is the only thing a move writes, and `ON DELETE SET NULL` returns a deleted shelf's files to
the root instead of taking them with it.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

revision: str = "0007_avatars_and_shelves"
down_revision: str | Sequence[str] | None = "0006_chacha20_poly1305"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_unicode_ci",
}

AVATAR_SHAPE = (
    "("
    "avatar_object_key IS NULL AND avatar_content_type IS NULL AND "
    "avatar_sha256 IS NULL AND avatar_bytes IS NULL AND avatar_updated_at IS NULL"
    ") OR ("
    "avatar_object_key IS NOT NULL AND "
    "avatar_content_type COLLATE utf8mb4_bin IN ('image/png', 'image/jpeg') AND "
    "avatar_sha256 REGEXP '^[0-9a-f]{64}$' AND "
    "avatar_bytes BETWEEN 1 AND 524288 AND "
    "avatar_updated_at IS NOT NULL"
    ")"
)


def _count(sql: str) -> int:
    """Run a guard query, or return 0 when generating SQL offline with no connection."""
    if op.get_context().as_sql:
        return 0
    return op.get_bind().execute(sa.text(sql)).scalar_one()


def upgrade() -> None:
    op.create_table(
        "shelves",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False),
        sa.Column("shelf_uuid", sa.CHAR(length=36), nullable=False),
        sa.Column("owner_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column(
            "revision",
            mysql.INTEGER(unsigned=True),
            server_default="1",
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shelf_uuid", name="uq_shelves_shelf_uuid"),
        sa.UniqueConstraint("owner_id", "name", name="uq_shelves_owner_name"),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["users.id"],
            name="fk_shelves_owner",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        sa.CheckConstraint("CHAR_LENGTH(name) >= 1", name="ck_shelves_name_length"),
        sa.CheckConstraint("revision >= 1", name="ck_shelves_revision"),
        **TABLE_OPTIONS,
    )
    op.create_index("idx_shelves_owner_id", "shelves", ["owner_id"])

    op.add_column("files", sa.Column("shelf_id", mysql.BIGINT(unsigned=True), nullable=True))
    # Created before the foreign key so MySQL adopts it as the supporting index instead of
    # inventing one of its own, whose name the schema files would not record.
    op.create_index("idx_files_shelf_id", "files", ["shelf_id"])
    op.create_index("idx_files_owner_shelf", "files", ["owner_id", "shelf_id"])
    op.create_foreign_key(
        "fk_files_shelf",
        "files",
        "shelves",
        ["shelf_id"],
        ["id"],
        ondelete="SET NULL",
        onupdate="CASCADE",
    )

    op.add_column("users", sa.Column("avatar_object_key", sa.String(length=500), nullable=True))
    op.add_column("users", sa.Column("avatar_content_type", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("avatar_sha256", sa.CHAR(length=64), nullable=True))
    op.add_column("users", sa.Column("avatar_bytes", mysql.INTEGER(unsigned=True), nullable=True))
    op.add_column("users", sa.Column("avatar_updated_at", sa.DateTime(), nullable=True))
    op.create_unique_constraint("uq_users_avatar_object_key", "users", ["avatar_object_key"])
    op.create_check_constraint("ck_users_avatar_shape", "users", AVATAR_SHAPE)

    # Shelves are a first-class audit subject; without this value every SHELF_* append fails
    # at the enum, so create/rename/delete would commit nothing durable.
    op.execute(
        sa.text(
            "ALTER TABLE audit_logs MODIFY COLUMN resource_type ENUM("
            "'AUTH','USER','FILE','SHARE','RECOVERY','INTEGRITY','SYSTEM','SHELF'"
            ") NOT NULL"
        )
    )

    # Raise the readiness marker last, so a failure part-way never advertises a schema the
    # database does not have. The release gate compares this against the running code.
    op.execute(
        sa.text(
            f"ALTER TABLE audit_chain_heads ALTER COLUMN schema_revision SET DEFAULT '{revision}'"
        )
    )
    op.execute(sa.text(f"UPDATE audit_chain_heads SET schema_revision = '{revision}' WHERE id = 1"))


def downgrade() -> None:
    # An avatar's bytes live on disk and these columns are the only record of which object
    # belongs to which account. Dropping them with pictures still set would leave files
    # nothing can find, name, or remove, so refuse and say how to clear them first.
    # Offline SQL generation has no database to ask and skips the check.
    remaining = _count("SELECT COUNT(*) FROM users WHERE avatar_object_key IS NOT NULL")
    if remaining:
        raise RuntimeError(
            f"{remaining} account(s) still have an avatar. Their stored images would be "
            "orphaned on disk with nothing left to identify them. Remove the avatars "
            "first (POST /auth/avatar/delete, or clear the avatar_* columns), then "
            "downgrade."
        )

    # Lower the marker before removing anything. A database that still has the 0007
    # structures while advertising 0006 is merely ahead of the code, which ignores columns
    # it does not know; the reverse -- advertising 0007 after the columns are gone -- would
    # let 0007 code start against a schema that cannot serve it.
    op.execute(
        sa.text(
            "ALTER TABLE audit_chain_heads ALTER COLUMN schema_revision "
            f"SET DEFAULT '{down_revision}'"
        )
    )
    op.execute(
        sa.text(f"UPDATE audit_chain_heads SET schema_revision = '{down_revision}' WHERE id = 1")
    )

    op.drop_constraint("ck_users_avatar_shape", "users", type_="check")
    op.drop_constraint("uq_users_avatar_object_key", "users", type_="unique")
    op.drop_column("users", "avatar_updated_at")
    op.drop_column("users", "avatar_bytes")
    op.drop_column("users", "avatar_sha256")
    op.drop_column("users", "avatar_content_type")
    op.drop_column("users", "avatar_object_key")

    remaining_shelf_audits = _count(
        "SELECT COUNT(*) FROM audit_logs WHERE resource_type = 'SHELF'"
    )
    if remaining_shelf_audits:
        raise RuntimeError(
            f"{remaining_shelf_audits} audit row(s) still use resource_type SHELF. "
            "Clear or rewrite them before removing the enum value."
        )
    op.execute(
        sa.text(
            "ALTER TABLE audit_logs MODIFY COLUMN resource_type ENUM("
            "'AUTH','USER','FILE','SHARE','RECOVERY','INTEGRITY','SYSTEM'"
            ") NOT NULL"
        )
    )

    # The foreign key goes first: MySQL refuses to drop the index a live constraint needs.
    # Shelf assignments are lost here and the files return to the root, which is the same
    # state a shelf deletion already produces and costs no ciphertext.
    op.drop_constraint("fk_files_shelf", "files", type_="foreignkey")
    op.drop_index("idx_files_owner_shelf", table_name="files")
    op.drop_index("idx_files_shelf_id", table_name="files")
    op.drop_column("files", "shelf_id")
    op.drop_index("idx_shelves_owner_id", table_name="shelves")
    op.drop_table("shelves")
