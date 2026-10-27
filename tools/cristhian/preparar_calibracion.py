"""Une el conteo manual con el CSV agregado del detector y genera la entrada de calibrar.py.

El conteo manual suele hacerse en ventanas largas (por ejemplo 5 min) y el detector publica cada 30 s.
Para cada ventana manual se suman los intervalos automáticos del mismo carril y clase que caen
COMPLETOS dentro de la ventana. Si esos intervalos no cubren toda la ventana, la fila se rechaza
(no se comparan ventanas parciales o no sincronizadas).

Uso:
    python tools/cristhian/preparar_calibracion.py manual.csv resultados/conteos_cristhian.csv resultados/calibracion.csv
    python tools/cristhian/calibrar.py resultados/calibracion.csv resultados/calibracion_evaluada.csv

manual.csv: interseccion,acceso,carril,clase,inicio,fin,manual,prueba  (horas ISO 8601 con zona)
"""
import argparse
import csv
from datetime import datetime
from pathlib import Path

CLAVE = ['interseccion', 'acceso', 'carril', 'clase']
TOLERANCIA_S = 1.0


def fecha(texto):
    valor = datetime.fromisoformat(texto.replace('Z', '+00:00'))
    if valor.tzinfo is None:
        raise ValueError(f'Fecha sin zona horaria: {texto}')
    return valor


def unir(manual, automatico):
    salida = []
    for n, m in enumerate(manual, 2):
        ini, fin = fecha(m['inicio']), fecha(m['fin'])
        if fin <= ini:
            raise ValueError(f'Fila {n}: fin debe ser posterior a inicio')
        dentro = [a for a in automatico
                  if all(a[k] == m[k] for k in CLAVE)
                  and fecha(a['inicio']) >= ini and fecha(a['fin']) <= fin]
        cubierto = sum((fecha(a['fin']) - fecha(a['inicio'])).total_seconds() for a in dentro)
        ventana = (fin - ini).total_seconds()
        if cubierto < ventana - TOLERANCIA_S:
            raise ValueError(f'Fila {n}: el detector cubre {cubierto:.0f} s de {ventana:.0f} s; '
                             'ajustar la ventana manual a intervalos completos del detector')
        salida.append({**{k: m[k] for k in CLAVE}, 'inicio': m['inicio'], 'fin': m['fin'],
                       'manual': m['manual'], 'automatico': str(sum(int(a['cantidad']) for a in dentro)),
                       'prueba': m['prueba']})
    if not salida:
        raise ValueError('El CSV manual no tiene filas')
    return salida


def leer(ruta):
    with Path(ruta).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('manual', type=Path)
    p.add_argument('automatico', type=Path, help='CSV agregado que escribe cysa_detector.run')
    p.add_argument('salida', type=Path)
    a = p.parse_args()
    filas = unir(leer(a.manual), leer(a.automatico))
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    with a.salida.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    print(f'{len(filas)} ventanas preparadas. Siguiente: calibrar.py {a.salida} <salida_evaluada.csv>')


if __name__ == '__main__':
    main()
