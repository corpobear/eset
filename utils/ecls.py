import threading
import subprocess
import logging
import os
from queue import Queue

# Configure logging
logging.basicConfig(filename="process_logs.log", level=logging.DEBUG, 
                    format="%(asctime)s - %(levelname)s - %(message)s")


class EclsProcess:
    def __init__(self, path: str, batch_delimiter: str):
        self.path = path
        self.batch_delimiter = batch_delimiter
        self.process = None
        self.stdin = None
        self.stdout = None
        self.stderr = None
        self.lock = threading.Lock()

    def start(self):
        """Start the ecls.exe process."""
        self.process = subprocess.Popen(
            [self.path, "/log-all", "/stdin-filelist", f"/batch-delimiter={self.batch_delimiter}"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,  # Use binary mode
        )
        self.stdin = self.process.stdin
        self.stdout = self.process.stdout
        self.stderr = self.process.stderr

    def scan(self, file_data: bytes) -> str:
        """Send file data to the process and receive the output."""
        with self.lock:
            if self.process is None:
                raise RuntimeError("Process is not running.")

            # Write to the stdin of the process
            try:
                self.stdin.write(file_data)
            except:
                print(self.stderr.read())
            self.stdin.flush()

            # Signal the end of input for the batch
            self.stdin.write(f"{self.batch_delimiter}\n")
            self.stdin.flush()

            # Read the output until the batch delimiter
            result = []
            while True:
                line = self.stdout.readline()
                if not line or line.strip() == self.batch_delimiter:
                    break
                result.append(line.strip())

            return "\n".join(result)

    def stop(self):
        """Stop the process."""
        if self.process:
            self.process.terminate()
            self.process.wait()


class EclsManager:
    def __init__(self, ecls_path: str, batch_delimiter: str, num_processes: int):
        self.ecls_path = ecls_path
        self.batch_delimiter = batch_delimiter
        self.num_processes = num_processes
        self.process_pool = []
        self.queue = Queue()

    def initialize(self):
        """Initialize the process pool."""
        for _ in range(self.num_processes):
            process = EclsProcess(self.ecls_path, self.batch_delimiter)
            process.start()
            self.process_pool.append(process)

        # Create worker threads to process the queue
        for process in self.process_pool:
            threading.Thread(target=self._worker, args=(process,), daemon=True).start()

    def _worker(self, process: EclsProcess):
        """Worker thread for processing scan requests."""
        while True:
            file_data, result_future = self.queue.get()
            try:
                result = process.scan(file_data)
                result_future.set(result)
            except Exception as e:
                result_future.set(e)
            finally:
                self.queue.task_done()

    def submit_scan(self, file_data: bytes):
        """Submit a file for scanning."""
        result_future = Future()
        self.queue.put((file_data, result_future))
        return result_future.get()

    def shutdown(self):
        """Shutdown all processes."""
        for process in self.process_pool:
            process.stop()


class Future:
    """Simple Future class to store result or exception."""
    def __init__(self):
        self.result = None
        self.exception = None
        self._event = threading.Event()

    def set(self, result=None, exception=None):
        if exception:
            self.exception = exception
        else:
            self.result = result
        self._event.set()

    def get(self):
        self._event.wait()
        if self.exception:
            raise self.exception
        return self.result


ecls_manager = EclsManager("./ecls.exe", "__INPUT_END__", num_processes=4)
