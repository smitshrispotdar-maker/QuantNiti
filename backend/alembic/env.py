from alembic import context
from app.db import Base, engine
import app.models  # noqa: register tables
target_metadata = Base.metadata
with engine.connect() as conn:
    context.configure(connection=conn, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
