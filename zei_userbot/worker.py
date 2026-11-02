"""One account per process; EOF from Gate stops the account on parent failure."""
import asyncio
import json
import logging
import sys
import threading
from .runtime import Runtime


def watch_parent(loop, stopped):
    # A daemon reader works for inherited stdin pipes on both Windows and Linux.
    def read():
        try: sys.stdin.read()
        finally:
            try: loop.call_soon_threadsafe(stopped.set)
            except RuntimeError: pass
    threading.Thread(target=read,daemon=True).start()


async def main():
    logging.basicConfig(level=logging.CRITICAL)
    payload = json.loads(sys.stdin.readline())
    runtime = Runtime(payload["owner"], payload["credentials"], payload["path"], payload.get("helper", ""))
    payload.clear()
    parent_stopped = asyncio.Event()
    watch_parent(asyncio.get_running_loop(),parent_stopped)
    tasks = []
    try:
        await runtime.start()
        if parent_stopped.is_set(): return 1
        print("READY",flush=True)
        tasks = [asyncio.ensure_future(runtime.client.disconnected), asyncio.create_task(parent_stopped.wait())]
        await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
        return 0 if parent_stopped.is_set() else 1
    except Exception:
        print("FAILED",flush=True)
        return 1
    finally:
        for task in tasks: task.cancel()
        if tasks: await asyncio.gather(*tasks,return_exceptions=True)
        await runtime.stop()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
