"""Prueba automática de la placa MMU antes de usar el controlador.

Uso (con la placa conectada y el Monitor Serie de Arduino cerrado):
  python -m cysa_controlador.probar_placa --config controlador/config/demo_int_01.yaml --puerto COM3

Comprueba, en este orden:
  1. conexión y número de grupos (LISTO:n);
  2. un ciclo seguro completo, indicando qué LEDs deben verse en cada paso;
  3. que la placa se apaga en rojo intermitente si la PC deja de enviar (SIN_SENAL);
  4. que detecta dos verdes en conflicto (CONFLICTO);
  5. que detecta un ámbar demasiado corto (AMBAR_CORTO).
Entre las pruebas de falla reinicia la placa por el puerto (señal DTR); si la placa no se
reinicia sola, pide presionar RESET.
"""
import argparse
import time

from .plan import AMBAR, ROJO, VERDE
from .run import cargar_config

NOMBRES = {'G': 'VERDE', 'Y': 'AMBAR', 'R': 'ROJO'}


class Placa:
    def __init__(self, puerto, n, *, serial_factory=None, reloj=time.monotonic, dormir=time.sleep, preguntar=input):
        if serial_factory is None:
            import serial
            serial_factory = serial.Serial
        self.n, self.reloj, self.dormir, self.preguntar = n, reloj, dormir, preguntar
        self.puerto = serial_factory(puerto, 115200, timeout=0)
        self.buffer = ''

    def lineas(self):
        datos = self.puerto.read(256) or b''
        self.buffer += datos.decode('ascii', errors='replace')
        *completas, self.buffer = self.buffer.split('\n')
        return [l.strip() for l in completas if l.strip()]

    def esperar(self, prefijo, segundos):
        limite = self.reloj() + segundos
        while self.reloj() < limite:
            for linea in self.lineas():
                if linea.startswith(prefijo):
                    return linea
            self.dormir(0.05)
        return None

    def enviar_durante(self, luces, segundos):
        """Envía las luces cada 0,2 s durante el tiempo indicado. Devuelve las fallas recibidas."""
        fallas = []
        limite = self.reloj() + segundos
        while self.reloj() < limite:
            self.puerto.write(f'L:{"".join(luces)}\n'.encode('ascii'))
            fallas += [l for l in self.lineas() if l.startswith('FALLA:')]
            self.dormir(0.2)
        return fallas

    def reiniciar(self):
        self.puerto.dtr = False
        self.dormir(0.2)
        self.puerto.dtr = True
        listo = self.esperar('LISTO:', 6)
        if listo is None:
            self.preguntar('La placa no se reinició sola. Presiona RESET en la placa y luego Enter: ')
            listo = self.esperar('LISTO:', 6)
        return listo is not None

    def cerrar(self):
        self.puerto.close()


def ciclo_seguro(cruce):
    """Un verde por grupo, con su ámbar y su todo rojo, usando los mínimos del cruce."""
    n = len(cruce.grupos)
    pasos = []
    for g in range(n):
        verde = tuple(VERDE if i == g else ROJO for i in range(n))
        ambar = tuple(AMBAR if i == g else ROJO for i in range(n))
        pasos += [(verde, 2.0), (ambar, cruce.ambar_min_s + 0.3), ((ROJO,) * n, cruce.todo_rojo_min_s)]
    return pasos


def probar(placa, cruce, imprimir=print):
    resultados = []

    def registrar(nombre, ok, detalle=''):
        resultados.append((nombre, ok, detalle))
        imprimir(f'  {"OK   " if ok else "FALLA"}  {nombre}{(" - " + detalle) if detalle else ""}')

    n = len(cruce.grupos)
    imprimir('1) Conexión')
    listo = placa.esperar('LISTO:', 6)
    if listo is None:
        registrar('La placa responde LISTO', False, 'revisar puerto, cable y que el programa mmu_cysa esté cargado')
        return resultados
    registrar('La placa responde LISTO', listo == f'LISTO:{n}', listo if listo != f'LISTO:{n}' else '')
    if listo != f'LISTO:{n}':
        return resultados

    imprimir('2) Ciclo seguro (mirar los LEDs)')
    fallas = []
    for luces, segundos in ciclo_seguro(cruce):
        imprimir('     ' + '  '.join(f'{g}={NOMBRES[l]}' for g, l in zip(cruce.grupos, luces)))
        fallas += placa.enviar_durante(luces, segundos)
    registrar('Ciclo seguro sin fallas', not fallas, ', '.join(fallas))

    imprimir('3) La PC deja de enviar: la placa debe pasar a rojo intermitente')
    falla = placa.esperar('FALLA:', 2.5)
    registrar('Detecta la pérdida de señal', falla == 'FALLA:SIN_SENAL', falla or 'sin respuesta')
    registrar('Se reinicia', placa.reiniciar())

    imprimir('4) Verdes en conflicto: la placa debe pasar a rojo intermitente')
    placa.enviar_durante((VERDE,) + (ROJO,) * (n - 1), 0.4)
    a, b = next(iter(cruce.conflictos))
    conflicto = tuple(VERDE if i in (a, b) else ROJO for i in range(n))
    fallas = placa.enviar_durante(conflicto, 0.6)
    registrar('Detecta el conflicto', 'FALLA:CONFLICTO' in fallas, ', '.join(fallas) or 'sin respuesta')
    imprimir('     Mirar que todos los rojos parpadean.')
    placa.dormir(3)
    registrar('Se reinicia', placa.reiniciar())

    imprimir('5) Ámbar demasiado corto')
    verde = (VERDE,) + (ROJO,) * (n - 1)
    ambar = (AMBAR,) + (ROJO,) * (n - 1)
    fallas = placa.enviar_durante(verde, 0.4) + placa.enviar_durante(ambar, 0.6)
    fallas += placa.enviar_durante((ROJO,) * n, 0.6)
    registrar('Detecta el ámbar corto', 'FALLA:AMBAR_CORTO' in fallas, ', '.join(fallas) or 'sin respuesta')
    registrar('Se reinicia', placa.reiniciar())
    placa.enviar_durante((ROJO,) * n, 0.4)
    return resultados


def main(argv=None):
    p = argparse.ArgumentParser(description='Prueba automática de la placa MMU')
    p.add_argument('--config', required=True)
    p.add_argument('--puerto', required=True)
    a = p.parse_args(argv)
    _, cruce, _, _ = cargar_config(a.config)
    try:
        placa = Placa(a.puerto, len(cruce.grupos))
    except OSError as error:
        p.error(f'No se pudo abrir {a.puerto}: {error}. Cerrar el Monitor Serie de Arduino si está abierto.')
    print(f'Probando la placa en {a.puerto} con {len(cruce.grupos)} grupos: {", ".join(cruce.grupos)}')
    try:
        resultados = probar(placa, cruce)
    finally:
        placa.cerrar()
    fallidas = [r for r in resultados if not r[1]]
    print('\nResultado:', 'TODO CORRECTO' if not fallidas else f'{len(fallidas)} prueba(s) con problemas')
    print('Al cerrar el puerto la placa pasa a rojo intermitente; se reinicia sola al iniciar el controlador.')
    return 0 if not fallidas else 1


if __name__ == '__main__':
    raise SystemExit(main())
