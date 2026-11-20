"""Una representación ejecutable compartida por SUMO y el controlador."""
import hashlib,json,math
from dataclasses import asdict
from cysa_controlador.plan import cargar_interseccion,cargar_plan

ACCESOS={'N':'NS','S':'NS','E':'EO','W':'EO'}
CONFIG={'interseccion':'DEMO_INT_01','grupos':['NS','EO'],'conflictos':[['NS','EO']],
        'tiempos_min':{'ambar_s':3,'todo_rojo_s':2,'verde_s':10}}
LONGITUDES={'NS':6.0,'EO':6.0}  # geometría del banco, no la decide quien solicita el plan

def huella(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()

def minimo_peatonal(grupo):return LONGITUDES[grupo]/.9+5

def validar(documento):
    if documento.get('interseccion')!='DEMO_INT_01' or documento.get('prueba') is not True:
        raise ValueError('Solo se admiten planes del banco DEMO_INT_01')
    if set(documento.get('verdes',{}))!={'NS','EO'}:raise ValueError('Se requieren NS y EO')
    for g,t in documento['verdes'].items():
        if isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t) or not minimo_peatonal(g)<=t<=90:
            raise ValueError('Verde fuera de límites técnicos o mínimo peatonal')
    if documento.get('primero') not in ('NS','EO'):raise ValueError('Grupo inicial inválido')
    cruce=cargar_interseccion(CONFIG)
    return cruce,cargar_plan(documento['plan_id'],fases(documento),cruce)

def fases(d):
    primero=d['primero'];segundo='EO' if primero=='NS' else 'NS'
    result=[]
    for grupo in (primero,segundo):
        for color,duracion in [('G',d['verdes'][grupo]),('Y',3),('R',2)]:
            result.append({'fase_id':grupo+'_'+color,'duracion_s':duracion,
                           'luces':{g:color if g==grupo else 'R' for g in ('NS','EO')}})
    return result

def proponer(filas,modo='webster',grupo=None):
    if not filas:raise ValueError('No hay conteos de cámara en el intervalo')
    vol={g:0.0 for g in ('NS','EO')};micros=dict.fromkeys(vol,0)
    inicios=[];fines=[]
    for r in filas:
        if r['interseccion']!='DEMO_INT_01' or r['prueba'] is not True or r['acceso'] not in ACCESOS:
            raise ValueError('Conteos ajenos al banco o sin marca de prueba')
        g=ACCESOS[r['acceso']];q=r['cantidad']
        if not isinstance(q,int) or isinstance(q,bool) or q<0:raise ValueError('Cantidad inválida')
        if r['clase'] not in ('auto','micro','moto'):raise ValueError('Clase inválida')
        vol[g]+=q*{'auto':1,'micro':2,'moto':.5}[r['clase']]
        if r['clase']=='micro':micros[g]+=q
        inicios.append(r['inicio']);fines.append(r['fin'])
    segundos=(max(fines)-min(inicios)).total_seconds()
    if segundos<=0 or not sum(vol.values()):raise ValueError('Intervalo vacío o sin vehículos')
    # Dos accesos opuestos por grupo; capacidad del grupo de dos carriles: 3600 PCU/h.
    y={g:vol[g]*3600/segundos/3600 for g in vol};total=sum(y.values())
    if total>=.95:raise ValueError('Demanda saturada: no se recomienda un plan con Webster')
    ciclo=max(40,min(120,(1.5*10+5)/(1-total)))
    verdes={g:round(max(minimo_peatonal(g),10,(ciclo-10)*y[g]/total),3) for g in vol}
    if modo not in ('webster','micros','emergencia'):raise ValueError('Modo inválido')
    if modo!='webster' and grupo not in verdes:raise ValueError('Selecciona el grupo de prioridad')
    if modo=='micros':
        if not micros[grupo]:raise ValueError('No hay micros detectados en el grupo solicitado')
        verdes[grupo]=min(90,verdes[grupo]+10) # una extensión de hasta 10 s en la fase de cada ciclo
    d={'plan_id':'OP_'+huella({'y':y,'modo':modo,'grupo':grupo})[:16],
       'interseccion':'DEMO_INT_01','prueba':True,'modo':modo,'primero':grupo if modo=='emergencia' else 'NS',
       'verdes':verdes,'extension_micro_s':10 if modo=='micros' else 0,
       'geometria_m':LONGITUDES,'metodo':'Webster','version':1}
    d['grupo_prioridad']=grupo
    validar(d)
    return d

def referencia():
    return {'plan_id':'DEMO_FIJO','interseccion':'DEMO_INT_01','prueba':True,'modo':'fijo',
            'primero':'NS','verdes':{'NS':30,'EO':30},'extension_micro_s':0,'geometria_m':LONGITUDES,'version':1}
