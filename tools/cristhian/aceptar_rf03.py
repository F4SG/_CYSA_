"""RF-03. Compara un tramo del video, tres carriles del mismo acceso y tres clases.

Uso: python aceptar_rf03.py calibracion.csv resultado.json
El CSV es la salida de preparar_calibracion.py para una sola ventana manual.
"""
import argparse
import csv
import json
from pathlib import Path

from calibrar import evaluate


def comparar(rows):
    filas = evaluate(rows)
    tramos = {(r['interseccion'], r['acceso'], r['inicio'], r['fin'], r['prueba'].lower()) for r in filas}
    if len(tramos) != 1:
        raise ValueError('Las nueve filas deben corresponder al mismo acceso y tramo del video')
    carriles = sorted({r['carril'] for r in filas})
    if len(carriles) != 3 or len(filas) != 9 or any(not c.strip() for c in carriles):
        raise ValueError('Se requieren tres carriles con auto, micro y moto en cada uno, incluidos los ceros')
    detalle = {}
    for carril in carriles:
        detalle[carril] = {r['clase']: {k: int(r[k]) for k in ('manual', 'automatico')}
                           for r in filas if r['carril'] == carril}
    manual = sum(int(r['manual']) for r in filas)
    automatico = sum(int(r['automatico']) for r in filas)
    diferencia = abs(automatico - manual)
    resultado = 'SIN_BASE_PORCENTUAL' if manual == 0 else ('CUMPLE' if diferencia * 5 <= manual else 'NO_CUMPLE')
    return dict(interseccion=filas[0]['interseccion'], acceso=filas[0]['acceso'],
                inicio=filas[0]['inicio'], fin=filas[0]['fin'], carriles=detalle,
                total_manual=manual, total_automatico=automatico,
                error_pct=100*diferencia/manual if manual else None, resultado=resultado)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('entrada', type=Path)
    parser.add_argument('salida', type=Path)
    args = parser.parse_args()
    with args.entrada.open(encoding='utf-8-sig', newline='') as stream:
        resultado = comparar(list(csv.DictReader(stream)))
    args.salida.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
    print(resultado['resultado'])
    return 0 if resultado['resultado'] == 'CUMPLE' else 1


if __name__ == '__main__':
    raise SystemExit(main())
