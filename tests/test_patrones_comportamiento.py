"""Patrones de comportamiento: Strategy (integrado en el detector), State y Command
(pruebas de concepto para el Sprint 2) y patrones que el código ya usa."""
import inspect
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml

from cysa_detector import run
from cysa_detector import asignacion as st
from cysa_detector.auto_lanes import AutoLanes
from cysa_detector.counter import Lane, LineCounter
from casos_comportamiento.state import ControladorConEstados
from casos_comportamiento.command import CambioConfiguracion, HistorialCambios

REPO = Path(__file__).resolve().parents[1]
PERFIL = REPO / 'deteccion/config/carriles_DEMO_INT_01.yaml'

ZONA_IZQ = ((0.0, 0.0), (0.3, 0.0), (0.3, 1.0), (0.0, 1.0))
ZONA_DER = ((0.3, 0.0), (0.6, 0.0), (0.6, 1.0), (0.3, 1.0))
CON_ZONAS = [Lane('N', 'N_0', (0.05, 0.5), (0.25, 0.5), polygon=ZONA_IZQ),
             Lane('N', 'N_1', (0.35, 0.5), (0.55, 0.5), polygon=ZONA_DER)]
SIN_ZONAS = [Lane('N', 'N_0', (0.1, 0.5), (0.3, 0.5)), Lane('N', 'N_1', (0.3, 0.5), (0.5, 0.5))]

# Dos autos bajan: el 1 por la izquierda (x=0.2) y el 2 por la derecha (x=0.4); el 3 va fuera (x=0.8).
TRAYECTORIAS = [[(1, 0.2, 0.3), (2, 0.4, 0.3), (3, 0.8, 0.3)], [(1, 0.2, 0.7), (2, 0.4, 0.7), (3, 0.8, 0.7)]]


class Cap:
    def __init__(self): self.n = 0
    def get(self, p): return 30
    def read(self):
        self.n += 1
        return (True, np.zeros((100, 100, 3), np.uint8)) if self.n <= len(TRAYECTORIAS) else (False, None)


class T(list):
    def cpu(self): return self
    def int(self): return self
    def tolist(self): return list(self)


class Model:
    def __init__(self): self.n = 0
    def track(self, frame, **k):
        objs = TRAYECTORIAS[self.n]; self.n += 1
        boxes = SimpleNamespace(xyxy=T([[x * 100 - 5, y * 100 - 10, x * 100 + 5, y * 100] for _, x, y in objs]),
                                id=T([i for i, _, _ in objs]), cls=T([2 for _ in objs]), conf=T([.9 for _ in objs]))
        return [SimpleNamespace(boxes=boxes)]


def contar_con_detector(lanes):
    source = run.CameraSource({'interseccion': 'DEMO_INT_01', 'prueba': True},
                              datetime.fromisoformat('2026-10-27T12:00:00-04:00'))
    eventos = list(source._loop(Cap(), Model(), LineCounter(lanes), {2: 'auto'}, 30, SimpleNamespace(CAP_PROP_FPS=5)))
    return {e.carril: e.cantidad for e in eventos if e.clase == 'auto'}


# ---------- Strategy (integrado) ----------

def test_strategy_se_elige_segun_el_perfil():
    assert isinstance(st.crear_asignador({}, CON_ZONAS), st.AsignacionPorZonas)
    assert isinstance(st.crear_asignador({}, SIN_ZONAS), st.AsignacionPorLineas)
    assert isinstance(st.crear_asignador({'auto_carriles': True}, [], AutoLanes()), st.AsignacionAutomatica)
    with pytest.raises(ValueError):
        st.crear_asignador({'auto_carriles': True}, [])


def test_strategy_detector_por_zonas_cuenta_cada_carril_y_no_cuenta_fuera():
    assert contar_con_detector(CON_ZONAS) == {'N_0': 1, 'N_1': 1}


def test_strategy_detector_solo_lineas_cada_carril_cuenta_lo_suyo():
    """Mismo escenario del error corregido en el commit 32ed535."""
    assert contar_con_detector(SIN_ZONAS) == {'N_0': 1, 'N_1': 1}


def test_strategy_fuera_de_zona_y_visor():
    zonas = st.AsignacionPorZonas(CON_ZONAS)
    assert zonas.asignar(9, (0.9, 0.5)) == (None, st.FUERA_DE_ZONA)
    assert not zonas.muestra_fuera_de_zona() and st.AsignacionPorLineas().muestra_fuera_de_zona()


def test_strategy_automatica_usa_los_carriles_aprendidos():
    auto = AutoLanes(); auto.lanes = CON_ZONAS
    lane, clave = st.AsignacionAutomatica(auto).asignar(1, (0.2, 0.4))
    assert lane.carril == 'N_0' and clave == ('N', 'N_0')


def test_strategy_el_detector_ya_no_decide_por_modo():
    codigo = inspect.getsource(run.CameraSource._loop)
    assert 'asignador.asignar' in codigo
    assert 'auto.assign' not in codigo


# ---------- State (prueba de concepto, controlador del Sprint 2) ----------

def test_state_sin_comunicacion_mas_de_60_s_pasa_a_local_seguro_y_vuelve():
    c = ControladorConEstados('DEMO_INT_01')
    c.tick(59); assert c.fase == 'NORMAL'
    c.tick(61); assert c.fase == 'LOCAL_SEGURO'
    assert c.estado().estado_controlador == 'desconectado'
    c.mensaje_centro(70); assert c.fase == 'NORMAL'


def test_state_emergencia_verde_en_maximo_10_s_tras_ambar_y_todo_rojo():
    c = ControladorConEstados('DEMO_INT_01')
    c.emergencia_detectada('N', 100); assert c.fase == 'EMERGENCIA_AMBAR'
    c.tick(103); assert c.fase == 'EMERGENCIA_TODO_ROJO'
    c.tick(105); assert c.fase == 'EMERGENCIA_VERDE'
    assert c.verde_emergencia_en - 100 <= 10


def test_state_emergencia_espera_el_despeje_peatonal():
    c = ControladorConEstados('DEMO_INT_01')
    c.despeje_peatonal_hasta = 108
    c.emergencia_detectada('N', 100)
    c.tick(104); assert c.fase == 'EMERGENCIA_ESPERA_DESPEJE'
    c.tick(108); assert c.fase == 'EMERGENCIA_AMBAR'


def test_state_local_seguro_no_atiende_prioridades():
    c = ControladorConEstados('DEMO_INT_01')
    c.tick(61)
    c.emergencia_detectada('N', 63)
    assert c.fase == 'LOCAL_SEGURO'
    assert [(a, b) for _, a, b in c.historial] == [('NORMAL', 'LOCAL_SEGURO')]


# ---------- Command (prueba de concepto, RF-02 y RF-16) ----------

def perfil():
    return yaml.safe_load(PERFIL.read_text(encoding='utf-8'))


def test_command_registra_y_revierte():
    original = perfil()
    h = HistorialCambios(perfil())
    h.aplicar(CambioConfiguracion('model', 'yolo26s.pt', 'franco', 'administrador', 'Decisión S1: YOLO26s'))
    r = h.registros()[0]
    assert (r.usuario, r.accion, r.clave, r.anterior, r.posterior) == ('franco', 'aplicar', 'model', 'yolo26n.pt', 'yolo26s.pt')
    h.revertir_ultimo('franco', 'Más falsos negativos')
    assert h.config == original
    assert [x.accion for x in h.registros()] == ['aplicar', 'revertir']


def test_command_solo_administrador_y_motivo_obligatorio():
    h = HistorialCambios(perfil())
    with pytest.raises(PermissionError):
        h.aplicar(CambioConfiguracion('model', 'x.pt', 'ana', 'operador', 'prueba'))
    with pytest.raises(ValueError):
        h.aplicar(CambioConfiguracion('model', 'x.pt', 'franco', 'administrador', ' '))
    assert h.registros() == ()


def test_command_revertir_una_clave_nueva_la_elimina():
    original = perfil()
    h = HistorialCambios(perfil())
    h.aplicar(CambioConfiguracion('model', 'yolo26s.pt', 'franco', 'administrador', 'm1'))
    h.aplicar(CambioConfiguracion('imgsz', 960, 'franco', 'administrador', 'm2'))
    h.revertir_ultimo('franco', 'r1'); h.revertir_ultimo('franco', 'r2')
    assert h.config == original


# ---------- Patrones que el código ya usa ----------

def test_template_method_ejecutar_es_comun_y_crear_fuente_varia():
    assert 'ejecutar' not in vars(run.CreadorCamara) and 'ejecutar' not in vars(run.CreadorVideo)
    assert 'crear_fuente' in vars(run.CreadorCamara) and 'crear_fuente' in vars(run.CreadorVideo)


def test_iterator_eventos_es_un_generador():
    assert inspect.isgeneratorfunction(run.CameraSource.eventos)
