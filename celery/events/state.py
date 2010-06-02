from carrot.utils import partition

from celery import states


class Thing(object):
    visited = False

    def __init__(self, **fields):
        self.update(fields)

    def update(self, fields, **extra):
        for field_name, field_value in dict(fields, **extra).items():
            setattr(self, field_name, field_value)



class Worker(Thing):
    alive = False

    def __init__(self, **fields):
        super(Worker, self).__init__(**fields)
        self.heartbeats = []

    def online(self, **kwargs):
        self.alive = True

    def offline(self, **kwargs):
        self.alive = False

    def heartbeat(self, timestamp=None, **kwargs):
        self.heartbeats.append(timestamp)
        self.alive = True


class Task(Thing):
    uuid = None
    name = None
    state = states.PENDING
    received = False
    accepted = False
    args = '[]'
    kwargs = '{}'
    eta = None
    retries = 0
    worker = None

    @property
    def ready(self):
        return self.state in states.READY_STATES

    def update(self, d, **extra):
        d = dict(d, **extra)
        if self.worker:
            self.worker.online()
        return super(Task, self).update(d)

    def received(self, timestamp=None, **fields):
        self.received = timestamp
        self.state = "RECEIVED"
        self.update(fields, timestamp=timestamp)

    def accepted(self, timestamp=None, **fields):
        self.state = "ACCEPTED"
        self.accepted = timestamp
        self.update(fields)

    def failed(self, timestamp=None, **fields):
        self.state = states.FAILURE
        self.failed = timestamp
        self.update(fields, timestamp=timestamp)

    def retried(self, timestamp=None, **fields):
        self.state = states.RETRY
        self.retried = timestamp
        self.update(fields, timestamp=timestamp)

    def succeeded(self, timestamp=None, **fields):
        self.state = states.SUCCESS
        self.suceeded = timestamp
        self.update(fields, timestamp=timestamp)


class State(object):

    def __init__(self, callback=None):
        self.workers = {}
        self.tasks = {}
        self.callback = callback
        self.group_handlers = {"worker": self.worker_event,
                               "task": self.task_event}

    def get_worker(self, hostname, **kwargs):
        try:
            worker = self.workers[hostname]
            worker.update(kwargs)
        except KeyError:
            worker = self.workers[hostname] = Worker(
                    hostname=hostname, **kwargs)
        return worker

    def get_task(self, uuid, **kwargs):
        try:
            task = self.tasks[uuid]
            task.update(kwargs)
        except KeyError:
            task = self.tasks[uuid] = Task(uuid=uuid, **kwargs)
        return task

    def worker_event(self, type, fields):
        hostname = fields.pop("hostname")
        worker = self.workers[hostname] = Worker(hostname=hostname)
        handler = getattr(worker, type)
        if handler:
            handler(**fields)

    def task_event(self, type, fields):
        uuid = fields.pop("uuid")
        hostname = fields.pop("hostname")
        worker = self.get_worker(hostname)
        task = self.get_task(uuid, worker=worker)
        handler = getattr(task, type)
        if handler:
            handler(**fields)

    def event(self, event):
        group, _, type = partition(event.pop("type"), "-")
        self.group_handlers[group](type, event)
        if self.callback:
            self.callback(self, event)

    def tasks_by_timestamp(self):
        return sorted(self.tasks.items(), key=lambda t: t[1].timestamp)

state = State()
