import subprocess
import uvicorn
import threading

from machine.server import machine

def run_dramatiq():
    def run_worker():
        # Run dramatiq worker for `my_tasks` module
        subprocess.run(["dramatiq", "worker", "--processes", "3"])

    threading.Thread(target=run_worker, daemon=True).start()


def run():
    uvicorn.run(
        app="machine.server:machine",
        host=machine.settings.APP_HOST,
        port=machine.settings.APP_PORT,
        reload=machine.settings.DEBUG
    )


if __name__ == "__main__":
#    run_dramatiq()
    run()
