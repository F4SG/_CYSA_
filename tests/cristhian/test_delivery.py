from csv import DictReader
from datetime import datetime, timedelta, timezone
from threading import Event
from uuid import uuid4

from cysa.contracts import Conteo
import pytest
from cysa_detector.delivery import QueuedPublisher


def test_importacion_de_video_guarda_conteos_sin_publicar_mqtt(tmp_path, monkeypatch):
    from cysa_detector import run

    def sin_broker(*args):
        pytest.fail('La importación de video no debe usar MQTT')

    monkeypatch.setattr(run, 'Publisher', sin_broker)
    start = datetime(2026, 11, 24, tzinfo=timezone.utc)

    class Detector:
        def ejecutar(self, guardar):
            guardar(Conteo(mensaje_id=uuid4(), interseccion='DEMO_VIDEO',
                           acceso='N', carril='N_0', clase='micro', cantidad=2,
                           inicio=start, fin=start + timedelta(seconds=30), prueba=True))

    csv = tmp_path / 'video.csv'
    assert run.guardar_conteos(Detector(), csv, solo_csv=True) == 0
    with csv.open(encoding='utf-8', newline='') as file:
        row, = DictReader(file)
    assert (row['interseccion'], row['clase'], row['cantidad']) == ('DEMO_VIDEO', 'micro', '2')


def test_puback_lento_no_bloquea_captura_y_se_conserva_orden():
    entered=Event();release=Event();received=[]
    class Pub:
        def publish(self,event):
            if event==1:
                entered.set()
                assert release.wait(2)
            received.append(event)
    delivery=QueuedPublisher(Pub())
    try:
        delivery.publish(1)
        assert entered.wait(1)
        delivery.publish(2)
        assert not release.is_set() and not received
    finally:
        release.set();delivery.__exit__(None,None,None)
    assert received==[1,2]


def test_fallo_puback_no_se_declara_entregado():
    class Pub:
        def publish(self,event):raise TimeoutError('Sin PUBACK')
    with pytest.raises(TimeoutError,match='Sin PUBACK'):
        with QueuedPublisher(Pub()) as delivery:delivery.publish('conteo')


def test_cola_acotada_falla_sin_crecer_ni_descartar_silenciosamente():
    entered=Event();release=Event()
    class Pub:
        def publish(self,event):entered.set();release.wait(2)
    delivery=QueuedPublisher(Pub(),capacity=1)
    try:
        delivery.publish('primero');assert entered.wait(1)
        with pytest.raises(RuntimeError,match='CSV'):delivery.publish('segundo')
        assert len(delivery.pending)==1
    finally:
        release.set();delivery.__exit__(None,None,None)
