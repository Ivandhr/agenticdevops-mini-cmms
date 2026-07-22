"""The v1 persisted schema (`data-model.md` § 2).

Importing this package imports every model, so `Base.metadata` is complete by
the time Alembic autogenerate inspects it. Anything that needs the metadata
imports it from here.
"""

from app.db import Base
from app.models.asset import Asset
from app.models.downtime_event import DowntimeEvent
from app.models.identity import Identity
from app.models.work_order import WorkOrder

__all__ = ["Asset", "Base", "DowntimeEvent", "Identity", "WorkOrder"]
