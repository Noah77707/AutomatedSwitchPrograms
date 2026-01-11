import sys, os, traceback, threading, faulthandler, time

LOG_PATH = os.path.join(os.path.dirname(__file__), "crash.log")

def log(msg: str):
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")

def _sys_excepthook(exc_type, exc, tb):
    log("UNCAUGHT EXCEPTION (main thread):\n" + "".join(traceback.format_exception(exc_type, exc, tb)))
    sys.__excepthook__(exc_type, exc, tb)

def _thread_excepthook(args: threading.ExceptHookArgs):
    log(f"UNCAUGHT EXCEPTION (thread {args.thread.name}):\n" +
         "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)))

sys.excepthook = _sys_excepthook
threading.excepthook = _thread_excepthook

faulthandler.enable(open(LOG_PATH, "a", encoding="utf-8"))
