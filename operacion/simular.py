"""SUMO real en procesos acotados, misma demanda/semilla y plan idéntico al despachado."""
import csv,json,subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree.ElementTree import parse,SubElement
from sumo_base import EscenarioSUMOBuilder,binary
from .planes import ACCESOS,fases,huella,minimo_peatonal,referencia,validar

def _escribir_demanda(filas,path):
    campos=['interseccion','acceso','carril','clase','cantidad','inicio','fin','prueba']
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=campos);writer.writeheader()
        for row in filas:
            d={k:row[k] for k in campos};d['prueba']=str(d['prueba']).lower()
            d['inicio']=d['inicio'].isoformat();d['fin']=d['fin'].isoformat();writer.writerow(d)

def _ejecutar(filas,d,out):
    validar(d);out.mkdir();demanda=out/'demanda.csv';_escribir_demanda(filas,demanda)
    esc=EscenarioSUMOBuilder().con_red_demo().con_demanda(demanda).con_salida(out/'escenario').construir()
    red=out/'escenario/red.net.xml';tree=parse(red);logic=tree.getroot().find("tlLogic[@id='C']")
    conexiones=[x for x in tree.getroot().findall('connection') if x.get('tl')=='C']
    n=max(int(x.get('linkIndex')) for x in conexiones)+1
    for x in list(logic):logic.remove(x)
    # Un todo rojo inicial representa el punto de cambio autorizado del controlador.
    SubElement(logic,'phase',duration='2',state='r'*n)
    for fase in fases(d):
        estado=['r']*n
        for x in conexiones:
            grupo=ACCESOS[x.get('from').split('_')[0]];color=fase['luces'][grupo]
            estado[int(x.get('linkIndex'))]={'G':'G','Y':'y','R':'r'}[color]
        SubElement(logic,'phase',duration=str(fase['duracion_s']),state=''.join(estado))
    tree.write(red,encoding='utf-8',xml_declaration=True)
    trip=out/'tripinfo.xml'
    command=[binary('sumo'),'-c',str(esc.config), '--seed','42','--tripinfo-output',str(trip),
             '--tripinfo-output.write-unfinished','true','--no-step-log','true','--duration-log.disable','true']
    result=subprocess.run(command,capture_output=True,text=True,timeout=90)
    if result.returncode:raise ValueError('SUMO no pudo completar el escenario; no se autoriza el plan')
    metrics={};completados=0
    for t in parse(trip).getroot().findall('tripinfo'):
        if float(t.get('arrival','-1'))<0:raise ValueError('Hay vehículos sin completar; comparación inválida')
        acceso=t.get('id').split('__')[0];clase=t.get('vType');delay=float(t.get('timeLoss'))
        for key in (acceso,'micro' if clase=='micro' else 'resto','total'):
            metrics.setdefault(key,[]).append(delay)
        completados+=1
    if completados!=esc.esperados:raise ValueError('SUMO no completó toda la demanda')
    return {k:sum(v)/len(v) for k,v in metrics.items()},completados

def evaluar(filas,plan):
    # Nunca acepta métricas suministradas por un cliente como evidencia de ejecución.
    with TemporaryDirectory(prefix='cysa-sumo-operacion-') as temp:
        a,n=_ejecutar(filas,referencia(),Path(temp)/'base')
        b,m=_ejecutar(filas,plan,Path(temp)/'candidato')
    motivos=[]
    mejora=100*(a['total']-b['total'])/max(a['total'],.001)
    if plan['modo']=='webster' and mejora<10:motivos.append('No alcanza reducción global de demora del 10 %')
    for acceso in ACCESOS:
        if acceso in a and b[acceso]>a[acceso]*1.15+.001:motivos.append('Aumento superior al 15 % en '+acceso)
    if plan['modo']=='micros':
        if 'micro' not in a or b['micro']>a['micro']*.9:motivos.append('Micros no mejoran al menos 10 %')
        if b.get('resto',0)>a.get('resto',0)*1.1+.001:motivos.append('El resto aumenta más del 10 %')
    validar(plan)
    return {'aprobada':not motivos,'motivos':motivos,'referencia':a,'candidato':b,
            'mejora_porcentaje':mejora,'vehiculos':n,'semilla':42,'sumo_real':True,
            'huella_plan':huella(plan),'minimo_peatonal':True,
            'prioridad_emergencia':'se aplica solo en un todo rojo seguro; se rechaza si la espera supera 10 s' if plan['modo']=='emergencia' else None}

def buscar(filas,plan):
    """Extensión condicional 1..10 s; no recomendar la primera que perjudique al resto."""
    if plan['modo']!='micros':return plan,evaluar(filas,plan)
    from copy import deepcopy
    grupo=plan['grupo_prioridad'];otro='EO' if grupo=='NS' else 'NS'
    base=plan['verdes'][grupo]-plan['extension_micro_s'];mejor=None
    for extension in (1,4,7,10):
        for ajuste in (0,4,8):
            candidato=deepcopy(plan);candidato['verdes'][grupo]=base+extension
            candidato['verdes'][otro]+=ajuste;candidato['extension_micro_s']=extension
            validacion=evaluar(filas,candidato)
            if mejor is None or (validacion['aprobada'],validacion['mejora_porcentaje'])>(mejor[1]['aprobada'],mejor[1]['mejora_porcentaje']):
                mejor=candidato,validacion
    return mejor
