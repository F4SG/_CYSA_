"""Publicación ordenada sin esperar PUBACK en el hilo de captura/inferencia.

El CSV se escribe antes de encolar. Un error o cola llena se propaga; no se
interpreta una entrega pendiente como confirmada ni se pierde el registro local.
"""
from collections import deque
from concurrent.futures import ThreadPoolExecutor

class QueuedPublisher:
    def __init__(self,publisher,capacity=64):
        self.publisher=publisher
        self.capacity=capacity
        self.pending=deque()
        self.executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='cysa-mqtt')

    def __enter__(self):return self

    def publish(self,event):
        while self.pending and self.pending[0].done():self.pending.popleft().result()
        if len(self.pending)>=self.capacity:
            raise RuntimeError('Cola MQTT llena; conteos conservados en CSV para reenvio')
        self.pending.append(self.executor.submit(self.publisher.publish,event))

    def __exit__(self,error_type,error,traceback):
        self.executor.shutdown(wait=True)
        if error_type is None:
            for future in self.pending:future.result()
