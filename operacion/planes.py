"""Una representación ejecutable compartida por SUMO y el controlador."""
import hashlib,json,math
from cysa_controlador.plan import cargar_interseccion,cargar_plan

ACCESOS={'N':'NS','S':'NS','E':'EO','W':'EO'}
CONFIG={'interseccion':'DEMO_INT_01','grupos':['NS','EO'],'conflictos':[['NS','EO']],
        'tiempos_min':{'ambar_s':3,'todo_rojo_s':2,'verde_s':10}}
LONGITUDES={'NS':6.0,'EO':6.0}  # geometría del banco, no la decide quien solicita el plan
TIEMPOS={'verde_min_s':10,'verde_max_s':90,'ambar_s':3,'todo_rojo_s':2,'extension_micro_s':10}
CRUCE_PEATONAL_S=5

def huella(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()).hexdigest()

def minimo_peatonal(grupo):return LONGITUDES[grupo]/.9+5

def tiempos(documento):
    valores=documento.get('tiempos',TIEMPOS)
    if set(valores)!=set(TIEMPOS) or any(type(v) not in (int,float) or not math.isfinite(v) for v in valores.values()):
        raise ValueError('Tiempos de configuración inválidos')
    if not (10<=valores['verde_min_s']<=valores['verde_max_s']<=90
            and 3<=valores['ambar_s']<=10 and 2<=valores['todo_rojo_s']<=10
            and 0<=valores['extension_micro_s']<=10):
        raise ValueError('La configuración excede los límites del banco')
    return valores

def fases_peatonales(todo_rojo):
    return [
        {'fase_id':'PEATON_CRUCE','duracion_s':CRUCE_PEATONAL_S,'luces':{'NS':'R','EO':'R'},'peatonal':'cruce','a_demanda':True},
        {'fase_id':'PEATON_DESPEJE','duracion_s':round(max(LONGITUDES.values())/.9,3),
         'luces':{'NS':'R','EO':'R'},'peatonal':'despeje'},
        {'fase_id':'PEATON_TODO_ROJO','duracion_s':todo_rojo,'luces':{'NS':'R','EO':'R'}},
    ]

def validar(documento):
    if documento.get('interseccion')!='DEMO_INT_01' or documento.get('prueba') is not True:
        raise ValueError('Solo se admiten planes del banco DEMO_INT_01')
    if set(documento.get('verdes',{}))!={'NS','EO'}:raise ValueError('Se requieren NS y EO')
    limites=tiempos(documento)
    for g,t in documento['verdes'].items():
        minimo=limites['verde_min_s'] if documento.get('version')==2 else minimo_peatonal(g)
        if isinstance(t,bool) or not isinstance(t,(int,float)) or not math.isfinite(t) or not minimo<=t<=limites['verde_max_s']:
            raise ValueError('Verde fuera de los límites técnicos')
    if documento.get('primero') not in ('NS','EO'):raise ValueError('Grupo inicial inválido')
    cruce=cargar_interseccion({**CONFIG,'tiempos_min':{**limites,'verde_s':limites['verde_min_s']}})
    return cruce,cargar_plan(documento['plan_id'],fases(documento),cruce)

def fases(d):
    primero=d['primero'];segundo='EO' if primero=='NS' else 'NS'
    result=[]
    limites=tiempos(d)
    for grupo in (primero,segundo):
        for color,duracion in [('G',d['verdes'][grupo]),('Y',limites['ambar_s']),('R',limites['todo_rojo_s'])]:
            result.append({'fase_id':grupo+'_'+color,'duracion_s':duracion,
                           'luces':{g:color if g==grupo else 'R' for g in ('NS','EO')}})
    if d.get('version')==2:
        result.extend(fases_peatonales(limites['todo_rojo_s']))
    return result

def proponer(filas,modo='webster',grupo=None,*,configuracion=None):
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
    limites=tiempos({'tiempos':configuracion['tiempos']} if configuracion else {})
    perdido=2*(limites['ambar_s']+limites['todo_rojo_s'])
    ciclo=max(40,min(120,(1.5*perdido+5)/(1-total)))
    verdes={g:round(max(limites['verde_min_s'],min(limites['verde_max_s'],(ciclo-perdido)*y[g]/total)),3) for g in vol}
    if modo not in ('webster','micros','emergencia'):raise ValueError('Modo inválido')
    if modo!='webster' and grupo not in verdes:raise ValueError('Selecciona el grupo de prioridad')
    extension=0
    if modo=='micros':
        if not micros[grupo]:raise ValueError('No hay micros detectados en el grupo solicitado')
        extension=round(min(limites['extension_micro_s'],limites['verde_max_s']-verdes[grupo]),3)
        if extension<=0:raise ValueError('La configuración no permite extender la prioridad')
        verdes[grupo]=round(verdes[grupo]+extension,3)
    d={'plan_id':'OP_'+huella({'y':y,'modo':modo,'grupo':grupo})[:16],
       'interseccion':'DEMO_INT_01','prueba':True,'modo':modo,'primero':grupo if modo=='emergencia' else 'NS',
       'verdes':verdes,'extension_micro_s':extension,'tiempos':limites,
       'geometria_m':LONGITUDES,'metodo':'Webster','version':2}
    if configuracion:
        d['configuracion_id']=configuracion['id']
        d['configuracion_version']=configuracion['version']
    d['grupo_prioridad']=grupo
    validar(d)
    return d

def referencia():
    return {'plan_id':'DEMO_FIJO','interseccion':'DEMO_INT_01','prueba':True,'modo':'fijo',
            'primero':'NS','verdes':{'NS':30,'EO':30},'extension_micro_s':0,'geometria_m':LONGITUDES,'version':2}
