import threading
import time
from queue import Queue
from copy import deepcopy

# -------------------------------
# Message Types
# -------------------------------
NORMAL = "NORMAL"
MARKER = "MARKER"

# -------------------------------
# Message Class
# -------------------------------
class Message:
    def __init__(self, msg_type, content=None):
        self.type = msg_type
        self.content = content

# -------------------------------
# Process (Distributed Node)
# -------------------------------
class Process:
    def __init__(self, pid, initial_state):
        self.pid = pid
        self.state = initial_state

        self.in_channels = {}
        self.out_channels = {}

        self.snapshot_taken = False
        self.local_snapshot = None
        self.channel_snapshots = {}

    def add_out_channel(self, target, channel):
        self.out_channels[target] = channel

    def add_in_channel(self, source, channel):
        self.in_channels[source] = channel
        self.channel_snapshots[source] = []

    def send_message(self, target, value):
        msg = Message(NORMAL, value)
        self.out_channels[target].put(msg)
        print(f"P{self.pid} sends {value} to P{target}")

    def start_snapshot(self):
        print(f"\nP{self.pid} initiates SNAPSHOT")
        self.record_local_state()
        for channel in self.out_channels.values():
            channel.put(Message(MARKER))

    def record_local_state(self):
        self.snapshot_taken = True
        self.local_snapshot = deepcopy(self.state)
        print(f"P{self.pid} records local state: {self.local_snapshot}")

    def receive(self, source, message):
        if message.type == MARKER:
            self.handle_marker(source)
        else:
            self.handle_normal(source, message)

    def handle_marker(self, source):
        print(f"P{self.pid} received MARKER from P{source}")
        if not self.snapshot_taken:
            self.record_local_state()
            self.channel_snapshots[source] = []
            for channel in self.out_channels.values():
                channel.put(Message(MARKER))
        else:
            print(f"P{self.pid} stops recording channel from P{source}")

    def handle_normal(self, source, message):
        if self.snapshot_taken:
            self.channel_snapshots[source].append(message.content)

        self.state += message.content
        print(f"P{self.pid} received {message.content} from P{source} | New state: {self.state}")

# -------------------------------
# Channel Listener
# -------------------------------
def channel_listener(source, target, channel):
    while True:
        if not channel.empty():
            msg = channel.get()
            target.receive(source, msg)
        time.sleep(0.1)

# -------------------------------
# Main Program
# -------------------------------
if __name__ == "__main__":

    n = int(input("Enter number of processes: "))
    processes = {}

    # Create processes
    for i in range(1, n + 1):
        state = int(input(f"Enter initial state of P{i}: "))
        processes[i] = Process(i, state)

    # Create channels (fully connected)
    channels = {}
    for i in range(1, n + 1):
        for j in range(1, n + 1):
            if i != j:
                ch = Queue()
                channels[(i, j)] = ch
                processes[i].add_out_channel(j, ch)
                processes[j].add_in_channel(i, ch)

                threading.Thread(
                    target=channel_listener,
                    args=(i, processes[j], ch),
                    daemon=True
                ).start()

    # User-defined messages
    m = int(input("\nEnter number of messages to send before snapshot: "))
    for _ in range(m):
        src = int(input("Sender process ID: "))
        dst = int(input("Receiver process ID: "))
        val = int(input("Message value (+/-): "))
        processes[src].send_message(dst, val)
        time.sleep(0.5)

    # Snapshot initiation
    initiator = int(input("\nEnter snapshot initiator process ID: "))
    processes[initiator].start_snapshot()

    # Allow system to stabilize
    time.sleep(3)

    # -------------------------------
    # Display Snapshot Result
    # -------------------------------
    print("\n===== GLOBAL SNAPSHOT RESULT =====")
    for p in processes.values():
        print(f"\nProcess P{p.pid}")
        print(f"Local State: {p.local_snapshot}")
        for src, msgs in p.channel_snapshots.items():
            print(f"Channel from P{src}: {msgs}")