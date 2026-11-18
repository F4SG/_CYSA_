"""Integration checks against real local SQL Server. Resets only CYSA_WebIII_Demo."""
import argparse, json, os, subprocess, time, urllib.request, urllib.error, uuid
from datetime import datetime, timezone
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--port',type=int,default=5184)
parser.add_argument('--exe',type=Path,help='Probar el servicio publicado en lugar de dotnet + DLL de desarrollo')
args=parser.parse_args()
root=Path(__file__).resolve().parents[1]
project=root/'src/Cysa.Web.Api'
dll=project/'bin/Debug/net10.0/Cysa.Web.Api.dll'
runtime=root/'runtime/webiii-integration'
runtime.mkdir(parents=True,exist_ok=True)
base=f'http://localhost:{args.port}'
environment=dict(os.environ,ASPNETCORE_ENVIRONMENT='Development',Security__Mode='Demo',Demo__Enabled='true',
    Evaluaciones__BaseUrl=base,Storage__Directory=str(runtime),Logging__LogLevel__Default='Warning')
evidence=[]
process=None
log=(runtime/'server.log').open('w',encoding='utf-8')
tokens={}

def call(method,path,body=None,profile='administrador',expect=200,headers=None,record=True):
    request_headers={'Content-Type':'application/json'}
    if profile in tokens:request_headers['Authorization']='Bearer '+tokens[profile]
    request_headers.update(headers or {})
    request=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers=request_headers)
    try:
        response=urllib.request.urlopen(request,timeout=90)
    except urllib.error.HTTPError as error:response=error
    raw=response.read().decode('utf-8')
    try:data=json.loads(raw) if raw else None
    except json.JSONDecodeError:data=raw
    assert response.status==expect,(method,path,response.status,data)
    if record:evidence.append({'operacion':method+' '+path,'codigoHttp':response.status,'capturadaUtc':datetime.now(timezone.utc).isoformat(),'location':response.headers.get('Location'),
        'resultado':data if not isinstance(data,list) or len(data)<4 else {'cantidadMostrada':len(data),'primerRegistro':data[0]}})
    return data,response.headers

def start():
    global process
    command=[str(args.exe.resolve())] if args.exe else ['dotnet',str(dll)]
    process=subprocess.Popen(command+['--urls',base],cwd=args.exe.resolve().parent if args.exe else project,env=environment,stdout=log,stderr=log)
    for _ in range(100):
        if process.poll() is not None:raise AssertionError('API stopped; inspect server.log')
        try:
            urllib.request.urlopen(base+'/health',timeout=1).close()
            for profile in ['administrador','operador','evaluador','operador-sin-mfa']:
                data,_=call('GET','/api/demo/acceso/'+profile,profile=None,record=False)
                tokens[profile]=data['token']
            return
        except (OSError,urllib.error.URLError):time.sleep(.2)
    raise AssertionError('API did not start')

def stop():
    if process and process.poll() is None:
        process.terminate()
        try:process.wait(10)
        except subprocess.TimeoutExpired:process.kill();process.wait(10)

def new(route,body):return call('POST','/api/'+route,body,expect=201)[0]
def check_counts():
    data,_=call('GET','/api/demo/base')
    assert data['preparada'] and len(data['tablas'])==26
    assert data['tablas']['Rol']==2
    assert all(n>=15 for table,n in data['tablas'].items() if table!='Rol')
    return data['tablas']

try:
    start()
    reset_header={'X-CYSA-Confirmar':'CYSA_WebIII_Demo'}
    call('POST','/api/demo/base',{},headers=reset_header)
    baseline=check_counts()
    catalog=json.loads((project/'wwwroot/resource-catalog.json').read_text(encoding='utf-8'))
    swagger,_=call('GET','/swagger/v1/swagger.json',profile=None,record=False)
    for resource in catalog:
        path='/api/'+resource['ruta']
        assert path in swagger['paths']
        rows,_=call('GET',path+'?tamano=200')
        assert len(rows)>= (2 if resource['entidad']=='Rol' else 15)
        call('GET',path+'/'+str(rows[0]['id']))
    call('GET','/api/intersecciones',profile=None,expect=401)
    call('GET','/api/intersecciones/999999',expect=404)
    call('GET','/api/intersecciones?pagina=0',expect=400)
    call('POST','/api/intersecciones',{},expect=400)
    call('POST','/api/intersecciones',{'corredorId':999999,'nombre':'Referencia inválida','latitud':-17,'longitud':-63,'estadoOperativo':'activo'},expect=400)
    call('POST','/api/corredores',{'nombre':'Sin permiso','descripcion':'Prueba'},profile='operador',expect=403)
    call('POST','/api/demo/base',{},profile='operador-sin-mfa',headers=reset_header,expect=403)
    call('POST','/api/demo/base',{},expect=400)
    assert check_counts()==baseline
    imported={'version':'1.0','mensaje_id':str(uuid.uuid4()),'interseccion':'DEMO_INT_01','acceso':'N','carril':'1','clase':'auto','cantidad':21,
              'inicio':'2026-11-18T11:59:30Z','fin':'2026-11-18T12:00:00Z','prueba':True}
    call('POST','/api/integracion/conteos',imported,profile='evaluador',expect=201)
    call('POST','/api/integracion/conteos',imported,profile='evaluador',expect=200)
    imported['cantidad']=22
    call('POST','/api/integracion/conteos',imported,profile='evaluador',expect=409)
    call('GET','/api/integracion/conteos?desde=2026-11-18T11:00:00Z&hasta=2026-11-18T13:00:00Z&interseccion=DEMO_INT_01')
    marker=str(uuid.uuid4())[:8]
    corridor=new('corredores',{'nombre':'Corredor '+marker,'descripcion':'Prueba HTTP de creación'})
    intersection=new('intersecciones',{'corredorId':corridor['id'],'nombre':'Cruce '+marker,'latitud':-17.78,'longitud':-63.18,'estadoOperativo':'activo'})
    approach=new('accesos',{'interseccionId':intersection['id'],'identificador':'N','aproximacion':'Norte','longitudCrucePeatonalMetros':18})
    related,_=call('GET',f'/api/intersecciones/{intersection["id"]}/accesos')
    assert [r['id'] for r in related]==[approach['id']]
    call('PUT',f'/api/intersecciones/{intersection["id"]}',{'corredorId':corridor['id'],'nombre':'Cruce actualizado '+marker,'latitud':-17.79,'longitud':-63.19,'estadoOperativo':'activo'},expect=204)
    lane=new('carriles',{'accesoId':approach['id'],'numero':1,'sentido':'entrada'})
    camera=new('fuentes-deteccion',{'accesoId':approach['id'],'tipoCamara':'IP demo','ubicacion':'Norte','protocolo':'RTSP','activa':True,'modeloIa':'demo','umbralConfianza':.5})
    controller=new('controladores',{'interseccionId':intersection['id'],'tipo':'Emulado','protocolo':'MQTT/TLS','ubicacion':'Gabinete demo','emulado':True})
    now='2026-11-18T12:00:00Z'
    config=new('configuraciones',{'interseccionId':intersection['id'],'version':1,'verdeMinSegundos':10,'verdeMaxSegundos':60,'ambarSegundos':3,'todoRojoSegundos':2,'extensionPrioridadSegundos':10,'responsableTecnico':'Técnico de prueba','aprobadaUtc':now,'estado':'aprobada'})
    plan=new('planes',{'interseccionId':intersection['id'],'configTecnicaId':config['id'],'version':1,'tipo':'optimizado','metodoCalculo':'Datos de prueba','cicloSegundos':60,'calculadoUtc':now,'estado':'borrador'})
    phase_body={'planId':plan['id'],'accesoId':approach['id'],'orden':1,'tipo':'peatonal','verdeSegundos':30,'ambarSegundos':3,'todoRojoSegundos':2,'tiempoPeatonalSegundos':24.9}
    call('POST','/api/fases',phase_body,expect=400)
    phase_body['tiempoPeatonalSegundos']=25
    phase=new('fases',phase_body)
    call('POST','/api/fases-accesos',{'faseId':phase['id'],'accesoId':1},expect=400)
    second_access=new('accesos',{'interseccionId':intersection['id'],'identificador':'S','aproximacion':'Sur','longitudCrucePeatonalMetros':18})
    phase_link=new('fases-accesos',{'faseId':phase['id'],'accesoId':second_access['id']})
    call('DELETE',f'/api/fases-accesos/{phase_link["id"]}',expect=204)
    call('DELETE',f'/api/accesos/{second_access["id"]}',expect=204)
    new('estados-control',{'controladorLocalId':controller['id'],'planId':plan['id'],'faseId':phase['id'],'fechaUtc':now,'comunicacionDisponible':True,'modo':'central'})
    measurement={'carrilId':lane['id'],'fuenteDeteccionId':camera['id'],'mensajeId':str(uuid.uuid4()),'inicioUtc':'2026-11-18T11:59:00Z','finUtc':now,'claseVehiculo':'auto','cantidad':25,'colaEstimadaMetros':5}
    saved_measurement=new('mediciones',measurement)
    measurement['mensajeId']=str(uuid.uuid4());measurement['fuenteDeteccionId']=1
    call('POST','/api/mediciones',measurement,expect=400)
    saved_event=new('eventos-prioridad',{'interseccionId':intersection['id'],'planId':plan['id'],'tipo':'emergencia','origen':'emulador','detectadoUtc':now,'atendidoUtc':'2026-11-18T12:00:08Z','resultado':'atendido','accion':'extension','extensionSegundos':8,'ciclo':1})
    new('alertas',{'interseccionId':intersection['id'],'tipo':'comunicacion','fechaUtc':now,'severidad':'informativa','descripcion':'Prueba de alerta','estado':'abierta'})
    validation=new('validaciones-sumo',{'planId':plan['id'],'escenario':'Escenario sintético HTTP','semilla':1,'ejecutadaUtc':now,'resultado':'aprobada','motivo':'Prueba sintética','demoraGlobalBaseSegundos':40,'demoraGlobalCandidataSegundos':32,'cumpleMinimoPeatonal':True,'cumpleDespejePeatonal':True})
    new('validaciones-mediciones',{'validacionSumoId':validation['id'],'medicionId':saved_measurement['id']})
    new('validaciones-eventos',{'validacionSumoId':validation['id'],'eventoPrioridadId':saved_event['id']})
    call('POST','/api/validaciones-mediciones',{'validacionSumoId':validation['id'],'medicionId':1},expect=400)
    call('POST','/api/validaciones-eventos',{'validacionSumoId':validation['id'],'eventoPrioridadId':1},expect=400)
    for group,vehicles in [('total',100),('micro',20),('resto',80)]:
        new('metricas-acceso',{'validacionSumoId':validation['id'],'accesoId':approach['id'],'grupo':group,'vehiculosBase':vehicles,'vehiculosCandidatos':vehicles,'demoraBaseSegundos':40,'demoraCandidataSegundos':32})
    new('recomendaciones',{'validacionSumoId':validation['id'],'emitidaUtc':now,'justificacionTecnica':'Mejora sintética del 20 %; peatones respetados'})
    normalized_decision={'solicitudId':str(uuid.uuid4()),'validacionSumoId':validation['id'],'accion':'autorizar','motivo':'Revisado con mínimo peatonal y métricas coherentes'}
    control_path=f'/api/planes/{plan["id"]}/decisiones-control'
    call('POST',control_path,normalized_decision,profile='operador-sin-mfa',expect=403)
    call('POST',control_path,normalized_decision,profile='administrador',expect=403)
    call('POST',control_path,normalized_decision,profile='operador',expect=201)
    call('POST',control_path,normalized_decision,profile='operador',expect=200)
    normalized_decision['solicitudId']=str(uuid.uuid4())
    call('POST',control_path,normalized_decision,profile='operador',expect=409)
    call('GET',control_path)
    new('usuarios',{'rolId':2,'identificadorIdp':'test-'+marker,'nombre':'Perfil de prueba HTTP','activo':True,'mfaHabilitado':True})
    call('PUT','/api/bitacoras/1',{},expect=405)
    call('DELETE','/api/validaciones-sumo/1',expect=405)
    call('DELETE',f'/api/intersecciones/{intersection["id"]}',expect=409)
    disposable=new('intersecciones',{'corredorId':corridor['id'],'nombre':'Temporal '+marker,'latitud':-17,'longitud':-63,'estadoOperativo':'inactivo'})
    call('DELETE',f'/api/intersecciones/{disposable["id"]}',expect=204)
    call('GET',f'/api/intersecciones/{disposable["id"]}',expect=404)
    evaluation_input={'planId':'HTTP_'+marker,'version':1,'interseccionId':'DEMO_INT_01','planBaseId':'FIJO_HTTP','escenario':'Prueba de contratos existentes','origen':'demo',
        'accesos':[{'id':'N','demoraBaseSegundos':40,'demoraCandidataSegundos':32,'longitudCruceMetros':18}],
        'fases':[{'id':'P1','accesos':['N'],'tiempoPeatonalSegundos':25}]}
    evaluation,_=call('POST','/api/evaluaciones',evaluation_input,profile='evaluador',expect=201)
    call('POST','/api/evaluaciones',evaluation_input,profile='evaluador',expect=409)
    decision={'solicitudId':str(uuid.uuid4()),'evaluacionId':evaluation['id'],'version':1,'accion':'autorizar','motivo':'Cumple los criterios sintéticos de prueba'}
    decision_path='/api/planes/'+evaluation_input['planId']+'/decisiones'
    call('POST',decision_path,decision,profile='operador',expect=201)
    call('POST',decision_path,decision,profile='operador',expect=200)
    call('POST','/api/demo/base',{},headers=reset_header)
    assert check_counts()==baseline
    call('GET',f'/api/intersecciones/{intersection["id"]}',expect=404)
    saved=new('intersecciones',{'corredorId':1,'nombre':'PERSISTENCIA_HTTP_'+marker,'latitud':-17.78,'longitud':-63.18,'estadoOperativo':'activo'})
    before,_=call('GET','/api/intersecciones/'+str(saved['id']))
    before_pid=process.pid
    stop();start()
    after,_=call('GET','/api/intersecciones/'+str(saved['id']))
    assert before==after
    evidence.append({'operacion':'REINICIO REAL + GET /api/intersecciones/'+str(saved['id']),'codigoHttp':200,'resultado':after,'persistenciaConfirmada':True,
        'pidAntes':before_pid,'pidDespues':process.pid,'sinRecreacionEntreLecturas':True,'capturadaUtc':datetime.now(timezone.utc).isoformat()})
    # Deja una semilla limpia para la revisión del usuario.
    call('DELETE','/api/intersecciones/'+str(saved['id']),expect=204)
    final=check_counts()
    result={'resultado':'PASS','pruebas':len(evidence),'tablasIniciales':baseline,'tablasFinales':final,'evidencias':evidence}
    (runtime/'evidencias.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'resultado':'PASS','pruebas':len(evidence),'persistenciaTrasReinicio':True,'recreacionRepetida':True,'tablas':len(baseline)},ensure_ascii=False))
finally:
    stop();log.close()
