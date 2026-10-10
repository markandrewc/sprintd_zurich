"""Ein Modell, das erst bei Bedarf auf die GPU geladen und nach einer Zeit ohne Anfrage wieder entladen wird.

So belegt ein Dienst nur VRAM, solange er arbeitet, und gibt ihn danach für andere Dienste frei. Was bleibt, ist der
CUDA-Kontext des Prozesses (einige hundert MB).

    slot = ModelSlot("kev", loader=Kev, idle_seconds=120)
    with slot.use() as kev:         # lädt beim ersten Mal; Anfragen laufen nacheinander
        kev.decide(...)
    slot.unload()                   # sofort freigeben (sonst nach idle_seconds automatisch)
"""
import gc
import threading
import time
from contextlib import contextmanager


class ModelSlot:
    def __init__(self, name, loader, idle_seconds):
        self.name, self.loader, self.idle_seconds = name, loader, idle_seconds
        self.model, self.last_used = None, 0.0
        self.lock = threading.Lock()   # ein Modell auf einer GPU: Anfragen nacheinander, Entladen nie mitten in einer Anfrage
        if idle_seconds > 0:
            threading.Thread(target=self._watch, name=f"{name}-idle", daemon=True).start()

    @contextmanager
    def use(self):
        with self.lock:
            if self.model is None:
                self.model = self.loader()
            try:
                yield self.model
            finally:
                self.last_used = time.monotonic()

    def unload(self):
        """Gibt das Modell und seinen VRAM frei. -> True, wenn etwas entladen wurde."""
        with self.lock:
            return self._unload()

    def _unload(self):
        if self.model is None: return False
        self.model = None
        gc.collect()
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            print(f"[{self.name}] entladen, {torch.cuda.memory_allocated() / 2**30:.1f} GB VRAM belegt", flush=True)
        return True

    def status(self):
        loaded = self.model is not None
        return {"loaded": loaded, "idle_seconds": round(time.monotonic() - self.last_used) if loaded else None,
                "unload_after_seconds": self.idle_seconds}

    def _watch(self):
        while True:
            time.sleep(min(5, self.idle_seconds))
            if self.model is None or time.monotonic() - self.last_used < self.idle_seconds:
                continue
            if self.lock.acquire(blocking=False):   # nur entladen, wenn gerade keine Anfrage läuft
                try:
                    if self.model is not None and time.monotonic() - self.last_used >= self.idle_seconds:
                        self._unload()
                finally:
                    self.lock.release()
