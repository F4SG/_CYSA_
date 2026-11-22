"""Controlador emulado del Sprint 2: planes seguros, State (RF-06), MMU y ciclo completo."""
from pathlib import Path

import pytest

from cysa.contracts import Estado, Latido
from cysa_controlador.centro import CentroSimulado, SinCentro
from cysa_controlador.controlador import ControladorEmulado
from cysa_controlador.mmu import MMUSerial, MMUSimulada, ReglasMMU
from cysa_controlador.plan import Fase, Plan, cargar_interseccion, cargar_plan, validar_plan
from cysa_controlador.run import cargar_config, ejecutar, main
from cysa_controlador.secuenciador import Secuenciador

REPO = Path(__file__).resolve().parents[2]
CONFIG = REPO / 'controlador/config/demo_int_01.yaml'


@pytest.fixture
def demo():
    datos, cruce, centro, local = cargar_config(CONFIG)
    return cruce, centro, local


def fases(*definiciones):
    return tuple(Fase(f'F{i}', d, tuple(l)) for i, (d, l) in enumerate(definiciones))


# ---------- planes ----------

def test_config_demo_es_valida(demo):
    cruce, centro, local = demo
    assert cruce.grupos == ('NS', 'EO')
    assert centro.plan_id == 'DEMO_FIJO' and local.plan_id == 'LOCAL_SEGURO'
    assert sum(f.duracion_s for f in centro.fases if not f.fase_id.startswith('PEATON')) == 70


@pytest.mark.parametrize('definicion, error', [
    (((30, 'GG'), (3, 'YR'), (2, 'RR')), 'conflicto'),
    (((30, 'GR'), (2, 'RR'), (30, 'RG'), (3, 'RY'), (2, 'RR')), 'sin ámbar'),
    (((30, 'GR'), (2, 'YR'), (2, 'RR'), (30, 'RG'), (3, 'RY'), (2, 'RR')), 'ámbar menor'),
    (((30, 'GR'), (3, 'YR'), (30, 'RG'), (3, 'RY')), 'todo rojo'),
    (((3, 'YR'), (2, 'RR'), (30, 'GR'), (3, 'YR')), 'primera fase'),
    (((30, 'GR'), (3, 'YR'), (30, 'GR'), (3, 'YR'), (2, 'RR')), 'ámbar a verde'),
    (((5, 'GR'), (3, 'YR'), (2, 'RR')), 'verde menor'),
])
def test_planes_inseguros_se_rechazan(demo, definicion, error):
    cruce = demo[0]
    with pytest.raises(ValueError) as e:
        validar_plan(Plan('P', fases(*definicion)), cruce)
    assert error in str(e.value) or error.split()[0] in str(e.value)


def test_config_exige_la_luz_de_cada_grupo(demo):
    cruce = demo[0]
    with pytest.raises(ValueError):
        cargar_plan('P', [{'fase_id': 'F1', 'duracion_s': 30, 'luces': {'NS': 'G'}}], cruce)


def test_interseccion_requiere_conflictos():
    with pytest.raises(ValueError):
        cargar_interseccion({'interseccion': 'X', 'grupos': ['NS', 'EO'], 'conflictos': []})


# ---------- secuenciador ----------

def test_secuenciador_recorre_las_fases_con_sus_tiempos(demo):
    _, centro, _ = demo
    s = Secuenciador(centro, 0)
    s.tick(29.9); assert s.fase.fase_id == 'F1_NS_VERDE'
    s.tick(30); assert s.fase.fase_id == 'F1_NS_AMBAR'
    s.tick(35); assert s.fase.fase_id == 'F2_EO_VERDE'
    s.tick(70); assert s.fase.fase_id == 'F1_NS_VERDE'


def test_cambio_de_plan_solo_al_terminar_un_todo_rojo(demo):
    _, centro, local = demo
    s = Secuenciador(centro, 0)
    s.tick(10); s.solicitar(local)
    s.tick(34); assert s.plan is centro          # sigue: ámbar y todo rojo del plan actual
    s.tick(35); assert s.plan is local and s.fase.fase_id == 'L1_NS_VERDE'


# ---------- State (RF-06) ----------

def nuevo(demo, ahora=0.0):
    cruce, centro, local = demo
    return ControladorEmulado(cruce, centro, local, True, ahora)


def test_arranca_en_local_seguro_y_pasa_a_centro_con_el_primer_latido(demo):
    c = nuevo(demo)
    assert c.modo.nombre == 'LOCAL_SEGURO' and c.plan_id == 'LOCAL_SEGURO'
    c.latido(1); c.tick(1)
    assert c.modo.nombre == 'CENTRO'
    assert c.plan_id == 'LOCAL_SEGURO'           # espera el todo rojo para cambiar
    c.tick(30.9); assert c.plan_id == 'LOCAL_SEGURO'
    c.tick(31); assert c.plan_id == 'DEMO_FIJO' and c.fase_id == 'F1_NS_VERDE'


def test_sin_latidos_mas_de_60_s_pasa_a_local_seguro(demo):
    c = nuevo(demo)
    c.latido(0); c.tick(0)
    c.tick(60); assert c.modo.nombre == 'CENTRO'
    c.tick(60.2); assert c.modo.nombre == 'LOCAL_SEGURO'
    assert c.estado().estado_controlador == 'desconectado'


def test_al_volver_la_comunicacion_regresa_al_centro(demo):
    c = nuevo(demo)
    c.latido(0); c.tick(0); c.tick(61)
    c.latido(80); c.tick(80)
    assert c.modo.nombre == 'CENTRO'
    assert [(a, b) for _, a, b in c.historial] == [('LOCAL_SEGURO', 'CENTRO'), ('CENTRO', 'LOCAL_SEGURO'), ('LOCAL_SEGURO', 'CENTRO')]


def test_falla_del_mmu_deja_intermitente_aunque_vuelva_el_centro(demo):
    c = nuevo(demo)
    c.falla_mmu('FALLA:CONFLICTO', 5)
    c.latido(6); c.tick(6); c.falla_mmu('FALLA:SIN_SENAL', 7)
    assert c.intermitente and c.luces is None and c.fase_id == 'INTERMITENTE'
    assert c.modo.motivo == 'FALLA:CONFLICTO'


def test_estado_cumple_el_contrato_y_planes_siguen_bloqueados(demo):
    c = nuevo(demo)
    estado = c.estado()
    assert isinstance(estado, Estado) and estado.interseccion == 'DEMO_INT_01' and estado.prueba is True
    Estado.model_validate_json(estado.model_dump_json())
    with pytest.raises(PermissionError):
        c.enviar_plan(None)


# ---------- MMU ----------

def reglas(demo):
    return ReglasMMU(demo[0])


def test_mmu_acepta_una_secuencia_segura(demo):
    m = reglas(demo)
    for t, luces in [(0, 'GR'), (30, 'YR'), (33, 'RR'), (35, 'RG')]:
        assert m.recibir(tuple(luces), t) is None


@pytest.mark.parametrize('secuencia, falla', [
    ([(0, 'GG')], 'CONFLICTO'),
    ([(0, 'GR'), (1, 'RR')], 'SIN_AMBAR'),
    ([(0, 'GR'), (30, 'YR'), (31, 'RR')], 'AMBAR_CORTO'),
    ([(0, 'GR'), (30, 'YR'), (34, 'GR')], 'AMBAR_A_VERDE'),
    ([(0, 'GX')], 'FORMATO'),
])
def test_mmu_detecta_fallas_y_queda_en_falla(demo, secuencia, falla):
    m = reglas(demo)
    respuesta = None
    for t, luces in secuencia:
        respuesta = m.recibir(tuple(luces), t)
    assert respuesta == f'FALLA:{falla}'
    assert m.recibir(('R', 'R'), 100) == f'FALLA:{falla}'      # no se rearma sola


def test_mmu_watchdog_sin_senal_de_la_pc(demo):
    m = reglas(demo)
    assert m.vigilar(10) is None                     # no se arma antes del primer mensaje
    m.recibir(('G', 'R'), 0)
    assert m.vigilar(0.9) is None and m.vigilar(1.1) == 'FALLA:SIN_SENAL'


class SerialFalso:
    def __init__(self, respuesta=b'LISTO:2\n'):
        self.entrada, self.escrito = respuesta, b''
    def read(self, n):
        datos, self.entrada = self.entrada[:n], self.entrada[n:]
        return datos
    def write(self, datos): self.escrito += datos
    def close(self): pass


def test_mmu_serial_espera_listo_y_envia_luces(demo):
    falso = SerialFalso(b'basura\nLISTO:2\nFALLA:CONFLICTO\n')
    m = MMUSerial('COM9', demo[0], serial_factory=lambda *a, **k: falso)
    m.enviar(('G', 'R'), 0)
    assert falso.escrito == b'L:GR\n'
    assert m.mensajes(0) == ['FALLA:CONFLICTO']


def test_mmu_serial_rechaza_placa_con_otros_grupos(demo):
    with pytest.raises(RuntimeError):
        MMUSerial('COM9', demo[0], serial_factory=lambda *a, **k: SerialFalso(b'LISTO:4\n'))
    with pytest.raises(TimeoutError):
        MMUSerial('COM9', demo[0], espera_s=0.1, serial_factory=lambda *a, **k: SerialFalso(b''))


# ---------- ciclo completo con reloj simulado ----------

class Reloj:
    def __init__(self): self.t = 0.0
    def __call__(self): return self.t
    def dormir(self, s): self.t = round(self.t + s, 6)


def correr(demo, centro, segundos, mmu=None):
    reloj = Reloj()
    c = nuevo(demo, 0.0)
    mmu = mmu or MMUSimulada(demo[0])
    lineas = []
    ejecutar(c, mmu, centro, reloj=reloj, dormir=reloj.dormir, duracion_s=segundos, imprimir=lineas.append)
    return c, mmu, lineas


def test_corte_de_comunicacion_completo_sin_fallas_del_mmu(demo):
    """El centro late, se corta a los 30 s y vuelve a los 150 s. El MMU nunca detecta una falla."""
    c, mmu, _ = correr(demo, CentroSimulado(0.0, (30, 150)), 400)
    transiciones = [(round(t), a, b) for t, a, b in c.historial]
    assert transiciones[0][1:] == ('LOCAL_SEGURO', 'CENTRO')
    (t_local, *_), = [x for x in transiciones if x[2] == 'LOCAL_SEGURO']
    assert 85 <= t_local <= 91                      # último latido (≤30 s) + 60 s
    assert any(x[2] == 'CENTRO' and 150 <= x[0] <= 156 for x in transiciones)
    assert mmu.reglas.falla is None and not c.intermitente
    assert c.plan_id == 'DEMO_FIJO'


def test_sin_centro_corre_siempre_el_plan_local(demo):
    c, mmu, _ = correr(demo, SinCentro(), 200)
    assert c.modo.nombre == 'LOCAL_SEGURO' and c.plan_id == 'LOCAL_SEGURO' and mmu.reglas.falla is None


def test_falla_inyectada_pone_el_banco_en_intermitente(demo):
    class MMUConConflicto(MMUSimulada):
        def mensajes(self, ahora):
            return super().mensajes(ahora) + (['FALLA:CONFLICTO'] if ahora >= 50 else [])
    c, _, lineas = correr(demo, CentroSimulado(0.0), 60, MMUConConflicto(demo[0]))
    assert c.intermitente and any('INTERMITENTE' in l for l in lineas)


def test_cli_con_mmu_simulado(capsys):
    assert main(['--config', str(CONFIG), '--sin-placa', '--duracion', '0.3']) == 0
    assert 'LOCAL_SEGURO' in capsys.readouterr().out


def test_latido_contrato():
    from datetime import datetime, timezone
    latido = Latido(timestamp=datetime.now(timezone.utc))
    assert Latido.model_validate_json(latido.model_dump_json()).version == '1.0'


def test_consumer_publica_latidos_mientras_esta_conectado():
    import threading
    from app.consumer import iniciar_latido

    class Cliente:
        def __init__(self): self.publicados, self.evento = [], threading.Event()
        def is_connected(self): return True
        def publish(self, topico, cuerpo, qos):
            self.publicados.append((topico, cuerpo, qos)); self.evento.set()

    c = Cliente()
    detener = iniciar_latido(c, intervalo_s=0.01)
    assert c.evento.wait(2)
    detener.set()
    topico, cuerpo, qos = c.publicados[0]
    assert topico == 'centro/latido' and qos == 1
    Latido.model_validate_json(cuerpo)


def test_credenciales_del_emulador(tmp_path, monkeypatch):
    from cysa_controlador.run import cargar_credenciales
    archivo = tmp_path / 'emulador.env'
    archivo.write_text('# comentario\nMQTT_USER=emulador\nMQTT_PORT=8883\n', encoding='utf-8')
    monkeypatch.delenv('MQTT_USER', raising=False)
    cargar_credenciales(archivo)
    import os
    assert os.environ['MQTT_USER'] == 'emulador'
    with pytest.raises(FileNotFoundError):
        cargar_credenciales(tmp_path / 'no_existe.env')


def test_acl_permite_el_latido_y_el_estado_del_emulador():
    acl = (REPO / 'infra/mosquitto/acl').read_text(encoding='utf-8').split('user ')
    usuarios = {bloque.splitlines()[0]: bloque for bloque in acl if bloque.strip()}
    assert 'topic write centro/latido' in usuarios['plataforma']
    assert 'topic read centro/latido' in usuarios['emulador'] and 'topic write corredor/+/estado' in usuarios['emulador']
    assert 'centro/latido' not in usuarios['deteccion']


# ---------- prueba de la placa y desconexión del cable ----------

class PlacaFalsa:
    """Imita la placa: aplica ReglasMMU con un reloj simulado y se reinicia con DTR."""
    def __init__(self, cruce, reloj, grupos=None):
        self.cruce, self.reloj = cruce, reloj
        self.n = grupos or len(cruce.grupos)
        self._dtr = True
        self._reiniciar()

    def _reiniciar(self):
        self.reglas = ReglasMMU(self.cruce)
        self.salida = f'LISTO:{self.n}\n'

    def read(self, n):
        falla = self.reglas.vigilar(self.reloj())
        if falla:
            self.salida += falla + '\n'
        datos, self.salida = self.salida[:n], self.salida[n:]
        return datos.encode()

    def write(self, datos):
        for linea in datos.decode().splitlines():
            falla = self.reglas.recibir(tuple(linea[2:]), self.reloj())
            if falla:
                self.salida += falla + '\n'

    @property
    def dtr(self): return self._dtr
    @dtr.setter
    def dtr(self, valor):
        if valor and not self._dtr:
            self._reiniciar()
        self._dtr = valor

    def close(self): pass


def test_prueba_de_placa_completa_con_placa_simulada(demo):
    from cysa_controlador.probar_placa import Placa, probar
    reloj = Reloj()
    falsa = PlacaFalsa(demo[0], reloj)
    placa = Placa('COM9', 2, serial_factory=lambda *a, **k: falsa, reloj=reloj, dormir=reloj.dormir,
                  preguntar=lambda *_: '')
    resultados = probar(placa, demo[0], imprimir=lambda *_: None)
    assert [r[0] for r in resultados] == ['La placa responde LISTO', 'Ciclo seguro sin fallas', 'Detecta la pérdida de señal',
                                          'Se reinicia', 'Detecta el conflicto', 'Se reinicia', 'Detecta el ámbar corto', 'Se reinicia']
    assert all(ok for _, ok, _ in resultados), resultados


def test_prueba_de_placa_avisa_si_tiene_otros_grupos(demo):
    from cysa_controlador.probar_placa import Placa, probar
    reloj = Reloj()
    falsa = PlacaFalsa(demo[0], reloj, grupos=4)
    placa = Placa('COM9', 2, serial_factory=lambda *a, **k: falsa, reloj=reloj, dormir=reloj.dormir)
    resultados = probar(placa, demo[0], imprimir=lambda *_: None)
    assert resultados == [('La placa responde LISTO', False, 'LISTO:4')]


def test_cable_desconectado_pone_el_controlador_en_intermitente(demo):
    class SerialQueSeDesconecta(SerialFalso):
        conectado = True
        def read(self, n):
            if not self.conectado:
                raise OSError('dispositivo desconectado')
            return super().read(n)
        def write(self, datos):
            if not self.conectado:
                raise OSError('dispositivo desconectado')
            super().write(datos)

    puerto = SerialQueSeDesconecta()
    mmu = MMUSerial('COM9', demo[0], serial_factory=lambda *a, **k: puerto)
    c = nuevo(demo)
    mmu.enviar(c.luces, 0)
    puerto.conectado = False
    mmu.enviar(c.luces, 0.2)
    for mensaje in mmu.mensajes(0.2):
        c.falla_mmu(mensaje, 0.2)
    assert c.intermitente and c.modo.motivo == 'FALLA:SIN_ENLACE'
