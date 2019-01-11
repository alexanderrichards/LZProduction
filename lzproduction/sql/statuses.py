"""Status enums for use in SQL tables."""
from enum import unique, Enum, IntEnum


__all__ = ('SERVICESTATUS', 'DIRACSTATUS', 'LOCALSTATUS')


@unique
class SERVICESTATUS(Enum):
    """Service Status Enum."""

    Unknown = 'lightgrey'
    Down = 'red'
    Up = 'brightgreen'  # pylint: disable=invalid-name


@unique
class DIRACSTATUS(IntEnum):
    """DIRAC Status Enum."""

    Unknown = 0
    Deleted = 1
    Killed = 2
    Done = 3
    Completed = 4
    Failed = 5
    Stalled = 6
    Running = 7
    Submitting = 8
    Received = 9
    Queued = 10
    Waiting = 11
    Checking = 12
    Matched = 13

    @property
    def local_status(self):
        """Convert to LOCALSTATUS."""
        return STATUS_MAP[self]

@unique
class LOCALSTATUS(IntEnum):
    """Local Status Enum."""

    Unknown = 0
    Deleted = 1
    Killed = 2
    Completed = 3
    Failed = 4
    Requested = 5
    Approved = 6
    Submitted = 7
    Submitting = 8
    Running = 9


STATUS_MAP = {DIRACSTATUS.Unknown: LOCALSTATUS.Unknown,
              DIRACSTATUS.Deleted: LOCALSTATUS.Deleted,
              DIRACSTATUS.Killed: LOCALSTATUS.Killed,
              DIRACSTATUS.Done: LOCALSTATUS.Completed,
              DIRACSTATUS.Completed: LOCALSTATUS.Running,
              DIRACSTATUS.Failed: LOCALSTATUS.Failed,
              DIRACSTATUS.Stalled: LOCALSTATUS.Failed,
              DIRACSTATUS.Running: LOCALSTATUS.Running,
              DIRACSTATUS.Submitting: LOCALSTATUS.Submitted,
              DIRACSTATUS.Received: LOCALSTATUS.Submitted,
              DIRACSTATUS.Queued: LOCALSTATUS.Submitted,
              DIRACSTATUS.Waiting: LOCALSTATUS.Submitted,
              DIRACSTATUS.Checking: LOCALSTATUS.Submitted,
              DIRACSTATUS.Matched: LOCALSTATUS.Submitted}
