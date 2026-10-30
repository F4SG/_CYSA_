"""Calcula errores sobre conteos suministrados; no genera resultados reales."""
import argparse,csv
from pathlib import Path
from datetime import datetime

def evaluate(rows):
    output=[];seen=set()
    for row in rows:
        if row['clase'] not in ['auto','micro','moto']:raise ValueError('Clase inválida')
        key=tuple(row[k] for k in ['interseccion','acceso','carril','clase','inicio','fin'])
        if key in seen:raise ValueError('Muestra duplicada')
        seen.add(key)
        start,end=[datetime.fromisoformat(row[k].replace('Z','+00:00')) for k in ['inicio','fin']]
        if start.tzinfo is None or end.tzinfo is None or end<=start:raise ValueError('Intervalo inválido o sin zona')
        manual,auto=int(row['manual']),int(row['automatico'])
        if manual<0 or auto<0:raise ValueError('Conteo negativo')
        if row['prueba'].lower() not in ['true','false']:raise ValueError('prueba debe ser true/false')
        error=abs(auto-manual)/manual*100 if manual else None
        output.append({**row,'error_pct':'' if error is None else f'{error:.4f}',
          'falsos_positivos':auto if manual==0 else '',
          'resultado':'SIN_BASE_PORCENTUAL' if error is None else ('CUMPLE' if error<=10 else 'NO_CUMPLE')})
    if not output:raise ValueError('Sin muestras: completar la plantilla con mediciones')
    return output

def main():
    p=argparse.ArgumentParser();p.add_argument('entrada',type=Path);p.add_argument('salida',type=Path);a=p.parse_args()
    with a.entrada.open(encoding='utf-8-sig',newline='') as f:rows=evaluate(list(csv.DictReader(f)))
    a.salida.parent.mkdir(parents=True,exist_ok=True)
    with a.salida.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    measured={r['clase'] for r in rows if r['prueba'].lower()=='false' and r['error_pct']!=''}
    print('Resultados calculados. Clases con muestras no sintéticas y base porcentual:',','.join(sorted(measured)) or 'ninguna')
    print('Revisar representatividad, todas las clases y cada resultado; este comando no aprueba RF-03 automáticamente.')
if __name__=='__main__':main()
