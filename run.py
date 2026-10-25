"""One-command launcher: python run.py
Starts the FastAPI backend (optional but nice) and the guided Streamlit dashboard.
Press Ctrl+C to stop both."""
import subprocess
import sys
import time

procs = []
try:
    procs.append(subprocess.Popen([sys.executable, "-m", "backend.main"]))
    time.sleep(2)
    procs.append(subprocess.Popen([sys.executable, "-m", "streamlit", "run",
                                   "simulation_streamlit/guided_app.py"]))
    procs[-1].wait()
except KeyboardInterrupt:
    pass
finally:
    for p in procs:
        p.terminate()
