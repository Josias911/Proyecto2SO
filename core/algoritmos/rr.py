from collections import deque
from .base import Estrategia

class RR(Estrategia):
    """
    Implementación de Round Robin siguiendo la interfaz de `Estrategia`.
    Mantiene una cola FIFO de listos y un contador de quantum restante.

    Convenciones con el Planificador:
      - add(p): meter proceso a la cola de listos.
      - elegir(actual): decide quién va a CPU (y reencola si agotó quantum).
      - pre_tick(actual): hook antes de ejecutar un tick (no hace nada aquí).
      - post_tick(actual): tras el tick, descuenta quantum y reencola si toca.
      - reinsertar(p): vuelve a meter p al final de la cola.
      - peek_ready()/dump_ready(): vistas de la cola para UI/depuración.
    """

    def __init__(self, qdef=2):
        super().__init__(qdef)
        self.ready = deque()
        self.qleft = 0  # quantum restante del proceso en CPU

    # --- API usada por el Planificador ---
    def add(self, p):
        """Añade un proceso a la cola de listos."""
        self.ready.append(p)

    def _reset_quantum(self, p):
        # Si el proceso trae quantum propio, úsalo; si no, usa el por defecto.
        self.qleft = int(p.quantum) if getattr(p, "quantum", None) else int(self.qdef)

    def elegir(self, actual):
        """
        Decide qué proceso corre a continuación.
        - Si hay uno en CPU con quantum > 0 y no terminó, continúa.
        - Si el actual terminó, se liberará y elegimos otro.
        - Si agotó quantum sin terminar, lo reencolamos y elegimos otro.
        - Si CPU está libre, tomamos el primero de la cola.
        """
        # Continuar si el actual aún tiene quantum y no terminó
        if actual is not None and self.qleft > 0 and not actual.terminado:
            return actual

        # Si el actual terminó, dejemos que el planificador lo finalice
        if actual is not None and actual.terminado:
            actual = None

        # Si agotó quantum (sin terminar), reencolar
        if actual is not None and self.qleft <= 0 and not actual.terminado:
            self.reinsertar(actual)
            actual = None

        # Elegir nuevo si CPU está libre
        if actual is None and self.ready:
            nuevo = self.ready.popleft()
            self._reset_quantum(nuevo)
            return nuevo

        # Puede regresar None si no hay listos
        return actual

    def pre_tick(self, actual):
        """Hook antes del tick de CPU (no se requiere lógica aquí)."""
        return None

    def post_tick(self, actual):
        """
        Después de consumir un tick de CPU:
        - Decrementa el quantum.
        - Si terminó, resetea contador.
        - Si se agotó y no terminó, reencola; el cambio efectivo lo hará
          el planificador en la siguiente llamada a `elegir`.
        """
        if actual is None:
            return None

        # Consumimos 1 unidad de quantum
        if self.qleft > 0:
            self.qleft -= 1

        if actual.terminado:
            self.qleft = 0
            return None

        if self.qleft <= 0:
            self.reinsertar(actual)

        return None

    def reinsertar(self, p):
        """Reinserta el proceso (p. ej., al agotar su quantum)."""
        self.ready.append(p)

    # Utilidades para UI/depuración
    def peek_ready(self):
        return list(self.ready)

    def dump_ready(self):
        return list(self.ready)
