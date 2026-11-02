"""initial schema"""
from app.db import Base, engine
import app.models  # noqa
revision = "0001"
down_revision = None
def upgrade():
    Base.metadata.create_all(bind=engine)  # idempotent: creates all QuantNiti tables
def downgrade():
    Base.metadata.drop_all(bind=engine)
