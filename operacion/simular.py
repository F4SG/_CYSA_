"""SUMO real en procesos acotados, misma demanda/semilla y plan idéntico al despachado."""
import csv,subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree.ElementTree import parse,SubElement
from sumo_base import EscenarioSUMOBuilder,binary,demo_network
from cysa_controlador.secuenciador import Secuenciador
from .planes import ACCESOS,huella,minimo_peatonal,referencia,tiempos,validar

def _escribir_demanda(filas,path):
    campos=['interseccion','acceso','carril','clase','cantidad','inicio','fin','prueba']
    with path.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=campos);writer.writeheader()
        for row in filas:
            d={k:row[k] for k in campos};d['prueba']=str(d['prueba']).lower()
            d['inicio']=d['inicio'].isoformat();d['fin']=d['fin'].isoformat();writer.writerow(d)

def secuencia_sumo(vigente, fin, *, candidato=None, evento=None):
    """Reproduce el secuenciador del banco, incluida una solicitud peatonal."""
    _, base=validar(vigente)
    prioridad=validar(candidato)[1] if candidato else None
    sec=Secuenciador(base,0)
    fases=[];activada=None;recuperada=None
    solicitud=60
    while sec.inicio < fin:
        fase,inicio=sec.fase,sec.inicio
        if evento is not None and inicio <= evento < inicio+fase.duracion_s and activada is None:
            corte=sec.corte_verde(evento,sec.plan.verde_min_s)
            demora=sec.hasta_cambio(evento,fin_verde=corte)
            protegido=0
            if fase.peatonal:
                protegido=inicio+fase.duracion_s-evento
                if fase.peatonal=='cruce':
                    protegido+=sec.plan.fases[(sec.indice+1)%len(sec.plan.fases)].duracion_s
            if demora > 10+protegido:
                raise ValueError('La prioridad no cabe en el plazo del escenario')
            sec.solicitar(prioridad,temporal=True,fin_verde=corte)
            activada=round(evento+demora,3)
        fin_fase=inicio+fase.duracion_s
        if sec.fin_verde is not None:
            fin_fase=min(fin_fase,sec.fin_verde)
        if solicitud is not None and inicio<=solicitud<fin_fase:
            sec.solicitar_cruce()
            solicitud=None
        if fin_fase>inicio:
            fases.append((fin_fase-inicio,fase))
        anterior=sec.plan
        sec.tick(fin_fase)
        if anterior is prioridad and sec.plan is base:
            recuperada=round(sec.inicio,3)
    if evento is None:
        return fases,None
    if activada is None or recuperada is None:
        raise ValueError('El escenario termina antes de recuperar el plan vigente')
    return fases,dict(evento_s=evento,verde_s=activada,demora_s=round(activada-evento,3),retorno_s=recuperada)

def _ejecutar(filas,d,out,evento=None,vigente=None):
    validar(d);out.mkdir();demanda=out/'demanda.csv';_escribir_demanda(filas,demanda)
    esc=EscenarioSUMOBuilder().con_red_demo().con_demanda(demanda).con_salida(out/'escenario').construir()
    red,_=demo_network(out/'escenario',peatonal=True)
    tree=parse(red);logic=tree.getroot().find("tlLogic[@id='C']")
    conexiones=[x for x in tree.getroot().findall('connection') if x.get('tl')=='C']
    cruces={e.get('id') for e in tree.getroot().findall('edge') if e.get('function')=='crossing'}
    peatones={int(x.get('linkIndex')) for x in conexiones if x.get('to') in cruces}
    if not peatones:
        raise ValueError('La red SUMO no contiene un cruce peatonal semaforizado')
    n=max(int(x.get('linkIndex')) for x in conexiones)+1
    for x in list(logic):logic.remove(x)
    fin=float(parse(esc.config).getroot().find('time/end').get('value'))
    fases,transicion=secuencia_sumo(d,fin) if evento is None else secuencia_sumo(vigente,fin,candidato=d,evento=evento)
    for duracion,fase in fases:
        estado=['r']*n
        for x in conexiones:
            indice=int(x.get('linkIndex'))
            grupo=ACCESOS.get(x.get('from').split('_')[0])
            if grupo:
                color=fase.luces[('NS','EO').index(grupo)]
                estado[indice]={'G':'G','Y':'y','R':'r'}[color]
            elif indice in peatones and fase.peatonal=='cruce':
                estado[indice]='G'
        SubElement(logic,'phase',duration=f'{duracion:.3f}',state=''.join(estado))
    tree.write(red,encoding='utf-8',xml_declaration=True)
    rutas=parse(esc.rutas)
    persona=SubElement(rutas.getroot(),'person',id='peaton_prueba',depart='0',departPos='295')
    SubElement(persona,'walk',edges='N_in N_out',arrivalPos='5',speed='0.9')
    # Los planes de rutas se leen en orden de salida.
    root=rutas.getroot();root.remove(persona)
    indice=next((i for i,elemento in enumerate(root) if elemento.tag=='flow'),len(root))
    root.insert(indice,persona)
    rutas.write(esc.rutas,encoding='utf-8',xml_declaration=True)
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
    peat= parse(trip).getroot().find("personinfo[@id='peaton_prueba']/walk")
    if peat is None or float(peat.get('arrival','-1'))<0:
        raise ValueError('SUMO no completó el cruce peatonal de prueba')
    return {k:sum(v)/len(v) for k,v in metrics.items()},completados,transicion

def evaluar(filas,plan,*,vigente=None):
    # Nunca acepta métricas suministradas por un cliente como evidencia de ejecución.
    vigente=vigente or referencia()
    with TemporaryDirectory(prefix='cysa-sumo-operacion-') as temp:
        emergencia=plan['modo']=='emergencia'
        base=vigente if emergencia else referencia()
        a,n,_=_ejecutar(filas,base,Path(temp)/'base')
        evento=None
        if emergencia:
            evento=max(0,vigente['verdes'][vigente['primero']]-.5)
        b,_,transicion=_ejecutar(filas,plan,Path(temp)/'candidato',evento,vigente)
        despeje=None
        if emergencia:
            fases,_=secuencia_sumo(vigente,600)
            transcurrido=0
            for duracion,fase in fases:
                if fase.peatonal=='despeje':
                    break
                transcurrido+=duracion
            else:
                raise ValueError('El plan vigente no contiene despeje peatonal')
            _,_,despeje=_ejecutar(filas,plan,Path(temp)/'emergencia-peatonal',transcurrido+1,vigente)
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
            'huella_plan':huella(plan),'minimo_peatonal':minimo_peatonal('NS'),
            'cruce_peatonal_sumo':True,
            'prioridad_emergencia':{'plan_previo':vigente['plan_id'],'sin_despeje':transicion,'con_despeje':despeje} if emergencia else None}

def buscar(filas,plan,*,vigente=None):
    """Extensión condicional 1..10 s; no recomendar la primera que perjudique al resto."""
    if plan['modo']!='micros':return plan,evaluar(filas,plan,vigente=vigente)
    from copy import deepcopy
    grupo=plan['grupo_prioridad'];otro='EO' if grupo=='NS' else 'NS'
    base=plan['verdes'][grupo]-plan['extension_micro_s'];mejor=None
    limite=plan['extension_micro_s'];maximo=tiempos(plan)['verde_max_s']
    for extension in sorted({min(n,limite) for n in (1,4,7,10)}):
        for ajuste in (0,4,8):
            candidato=deepcopy(plan);candidato['verdes'][grupo]=base+extension
            candidato['verdes'][otro]=min(maximo,candidato['verdes'][otro]+ajuste)
            candidato['extension_micro_s']=extension
            validacion=evaluar(filas,candidato)
            if mejor is None or (validacion['aprobada'],validacion['mejora_porcentaje'])>(mejor[1]['aprobada'],mejor[1]['mejora_porcentaje']):
                mejor=candidato,validacion
    return mejor
