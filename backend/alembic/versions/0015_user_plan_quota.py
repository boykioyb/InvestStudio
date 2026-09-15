"""users.plan + hạn mức riêng theo tài khoản

Ba cột phục vụ hạn mức ba tầng (riêng người → theo hạng → mức chung):

- `plan`              hạng tài khoản, mặc định 'free' (app/core/plans.py).
- `chat_daily_quota`  lượt hỏi trợ lý/ngày riêng của người. NULL = chưa đặt.
- `analyze_daily_quota` lượt phân tích/ngày riêng của người. NULL = chưa đặt.

NULL khác hẳn 0: NULL là "rơi xuống tầng dưới", 0 là "chặn sạch người này".

Revision ID: 0015
Revises: 0014
"""
import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def _co() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}


def upgrade() -> None:
    hien_co = _co()
    if "plan" not in hien_co:
        op.add_column("users", sa.Column("plan", sa.String(16), nullable=False,
                                         server_default="free"))
    if "chat_daily_quota" not in hien_co:
        op.add_column("users", sa.Column("chat_daily_quota", sa.Integer, nullable=True))
    if "analyze_daily_quota" not in hien_co:
        op.add_column("users", sa.Column("analyze_daily_quota", sa.Integer, nullable=True))


def downgrade() -> None:
    hien_co = _co()
    for cot in ("analyze_daily_quota", "chat_daily_quota", "plan"):
        if cot in hien_co:
            op.drop_column("users", cot)
