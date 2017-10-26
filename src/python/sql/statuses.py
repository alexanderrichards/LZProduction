from enum import unique, Enum, IntEnum


@unique
class SERVICESTATUS(Enum):
    Down = 0
    Up = 1


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
    Received = 8
    Queued = 9
    Waiting = 10
    Checking = 11
    Matched = 12

    @property
    def local_status(self):
        return STATUS_MAP[self]

@unique
class LOCALSTATUS(IntEnum):
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
              DIRACSTATUS.Received: LOCALSTATUS.Submitted,
              DIRACSTATUS.Queued: LOCALSTATUS.Submitted,
              DIRACSTATUS.Waiting: LOCALSTATUS.Submitted,
              DIRACSTATUS.Checking: LOCALSTATUS.Submitted,
              DIRACSTATUS.Matched: LOCALSTATUS.Submitted}
