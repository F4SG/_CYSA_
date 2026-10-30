import argparse,csv,time
from pathlib import Path
from datetime import datetime,timedelta,timezone
from uuid import uuid4
from cysa.contracts import Conteo
from cysa.interfaces import FuenteDeteccion
from cysa.mqtt import Publisher
from .counter import Lane,LineCounter
from .auto_lanes import AutoLanes
from .camera import open_source
from .inference import detection_settings
from .roi import crop_for_lanes,restore_box
from .delivery import QueuedPublisher

class CameraSource(FuenteDeteccion):
    def __init__(self,config,inicio_video=None):
        self.config=config
        self.edit_requested=False
        # inicio_video: hora real en que empezó la grabación. Activa el reloj del video (cuadro/fps)
        # en vez del reloj de la PC, para que los intervalos coincidan con un conteo manual del mismo video.
        if inicio_video is not None and (inicio_video.tzinfo is None or inicio_video.utcoffset() is None):
            raise ValueError('inicio_video requiere zona horaria, p. ej. 2026-10-31T07:00:00-04:00')
        self.inicio_video=inicio_video
    def eventos(self):
        import cv2
        from ultralytics import YOLO
        c=self.config
        if not c.get('interseccion') or (not c.get('auto_carriles') and not c.get('lanes')):raise ValueError('Completar intersección y líneas en YAML')
        if not isinstance(c.get('prueba'),bool):raise ValueError('prueba debe ser booleano')
        seconds=c.get('intervalo_s',30)
        if not isinstance(seconds,(int,float)) or not 1<=seconds<=30:raise ValueError('intervalo_s entre 1 y 30')
        source=c.get('source',0)
        if self.inicio_video is not None and isinstance(source,int):
            raise ValueError('El reloj de video solo aplica a archivos; la webcam usa la hora real')
        # stream/video externo se lee sin copiarlo; únicamente fuente secuencial, jamás paquetes de imágenes.
        cap=open_source(cv2,source,c)
        inference=None
        try:
            lanes=[Lane(x['acceso'],x['carril'],tuple(x['a']),tuple(x['b']),x['direction'],tuple(tuple(p) for p in x.get('polygon',[]))) for x in c.get('lanes',[])]
            if c.get('auto_carriles'):lanes=[]
            counter=LineCounter(lanes)
            model=YOLO(c.get('model','yolo26n.pt'))
            mapping={int(k):v for k,v in c['class_map'].items()}
            if c.get('async_inference',False):
                if not isinstance(source,int) or not c.get('capture_latest',False):
                    raise ValueError('async_inference requiere camara y capture_latest')
                from .live_inference import LiveInference
                options,_=detection_settings(c,mapping)
                inference=LiveInference(model,options)
            yield from self._loop(cap,model,counter,mapping,seconds,cv2,inference)
        finally:
            # Primero soltar la cámara/ventana; esperar después al único trabajo de IA.
            cap.release()
            if c.get('show',False):cv2.destroyAllWindows()
            if inference is not None:inference.close()
    def _loop(self,cap,model,counter,mapping,seconds,cv2,inference=None):
        c=self.config;video=self.inicio_video is not None
        track_options,class_thresholds=detection_settings(c,mapping)
        if video:
            fps=cap.get(cv2.CAP_PROP_FPS)
            if not fps or fps<=0:raise RuntimeError('El video no informa FPS; no se puede usar su reloj')
            base=self.inicio_video.astimezone(timezone.utc)
            clock=lambda n:n/fps
            wall=lambda t:base+timedelta(seconds=t)
        else:
            clock=lambda n:time.monotonic()
            wall=lambda t:datetime.now(timezone.utc)
        show=bool(c.get('show',False))
        window='CYSA - Deteccion vehicular'
        if show:
            from .preview import PreviewControls
            controls=PreviewControls()
            cv2.namedWindow(window,cv2.WINDOW_NORMAL)
            cv2.setMouseCallback(window,controls.click)
        totals={}
        automatic=bool(c.get('auto_carriles',False))
        auto=AutoLanes(c.get('acceso_auto','N'))
        ready=not automatic
        candidate=[];stable=0;last_attempt=None
        warmup=float(c.get('calibracion_s',12))
        if warmup<0:raise ValueError('calibracion_s no puede ser negativo')
        tick=clock(0);start=wall(tick);n=0
        calibration_start=tick
        preview_started=time.monotonic()
        cached_labels=[];labels_at=0
        def flush(end):
            counts=counter.snapshot()
            for lane in counter.lanes:
                for clase in ['auto','micro','moto']:
                    yield Conteo(mensaje_id=uuid4(),interseccion=c['interseccion'],acceso=lane.acceso,carril=lane.carril,
                      clase=clase,cantidad=counts.get((lane.acceso,lane.carril,clase),0),inicio=start,fin=end,prueba=c['prueba'])
        while True:
            if c.get("stop_file") and Path(c["stop_file"]).exists():break
            ok,frame=cap.poll(.015) if inference is not None else cap.read()
            if not ok:
                if inference is not None and not cap.finished:
                    if show:
                        controls.key(cv2.waitKey(1)&255,automatic)
                        self.edit_requested=controls.edit
                        if controls.stop or controls.edit or cv2.getWindowProperty(window,cv2.WND_PROP_VISIBLE)<1:break
                    continue
                break
            h,w=frame.shape[:2];n+=1
            if n==1:
                print(f'Resolucion recibida: {w}x{h}. Solicitada: {c.get("camera_width","predeterminada")}x{c.get("camera_height","predeterminada")}.',flush=True)
            inference_frame,offset=crop_for_lanes(frame,counter.lanes,c)
            captured_at=getattr(cap,'delivered_at',None) or time.monotonic()
            if inference is None:
                results=model.track(inference_frame,**track_options)
                result_at=captured_at
            else:
                completed=inference.take()
                # Sustituye el único pendiente por el más reciente; no acumula cuadros.
                inference.submit(inference_frame,offset,(h,w),captured_at)
                results=None;result_at=captured_at
                if completed is not None:
                    results,offset,shape,result_at,_=completed
                    if shape!=(h,w):results=None
            now_tick=clock(n)
            detections=[]
            boxes=results[0].boxes if results is not None else None
            if boxes is not None and boxes.id is not None:
                for xyxy,tid,cls,score in zip(boxes.xyxy.cpu().tolist(),boxes.id.int().cpu().tolist(),boxes.cls.int().cpu().tolist(),boxes.conf.cpu().tolist()):
                    if score<class_thresholds.get(cls,1.):continue
                    xyxy=restore_box(xyxy,offset)
                    x1,y1,x2,y2=xyxy
                    point=((x1+x2)/(2*w),y2/h)
                    detections.append((xyxy,tid,cls,point))
                    if automatic and not ready:auto.observe(tid,point,(x2-x1)/w,(y2-y1)/h,now_tick)
            if automatic and not ready:
                if now_tick-calibration_start>=warmup and (last_attempt is None or now_tick-last_attempt>=1):
                    last_attempt=now_tick
                    proposal=auto.infer()
                    matches=len(proposal)==len(candidate) and all(
                        max(abs(float(x)-float(y)) for x,y in zip(l.a+l.b,r.a+r.b))<.035
                        and l.direction==r.direction for l,r in zip(proposal,candidate))
                    stable=stable+1 if proposal and matches else 1 if proposal else 0
                    candidate=proposal
                    if stable>=3:
                        auto.lanes=proposal;counter=LineCounter(proposal);ready=True
                        self.calibrated_lanes=proposal
                        print(f'Carriles automaticos activos: {len(proposal)}. Conteo iniciado.',flush=True)
                # No publicar ceros ni contar el tiempo usado para calibrar.
                tick=now_tick;start=wall(tick)
            if ready and now_tick-tick>30.5:
                raise RuntimeError('Procesamiento demasiado lento: reducir resolucion/modelo o usar GPU')
            labels=[]
            for xyxy,tid,cls,point in detections:
                if automatic and ready:lane=auto.assign(tid,point)
                else:
                    # Solo una zona dibujada (polygon) asigna un vehículo a un carril. Un segmento sin zona
                    # "contiene" cualquier punto, así que no sirve para asignar: con él, el primer carril
                    # se quedaba con todos los vehículos y los demás contaban siempre 0.
                    lane=next((l for l in counter.lanes if l.polygon and l.contains(point)),None)
                if ready:
                    before=counter.snapshot()
                    if lane:key=(lane.acceso,lane.carril)
                    elif automatic or any(l.polygon for l in counter.lanes):key=('','')  # fuera de toda zona
                    else:key=None  # solo segmentos: decide el cruce de cada línea
                    counter.observe(tid,mapping.get(cls),point,now_tick,lane_key=key)
                    for k,value in counter.snapshot().items():
                        totals[k]=totals.get(k,0)+value-before.get(k,0)
                if lane or not ready or not any(l.polygon for l in counter.lanes) or c.get('show_outside_lanes',False):labels.append((xyxy,tid,cls,lane))
            if results is not None:
                cached_labels=labels;labels_at=result_at
            if inference is not None:
                # También descartar visualmente un resultado recién terminado pero ya viejo.
                # Su trayectoria ya se procesó arriba para contar; ocultar no borra conteos.
                labels=cached_labels if time.monotonic()-labels_at<=.18 else []
            counter.prune(now_tick)
            stop=False;recalibrate=False
            if show:
                # YOLO cierra sus ventanas al terminar cada llamada por cuadro.
                import numpy as np
                preview=frame.copy()
                palette=[(0,220,255),(0,255,100),(255,180,0),(255,100,200)]
                lane_colors={l.carril:palette[i%len(palette)] for i,l in enumerate(counter.lanes)}
                for xyxy,tid,cls,lane in labels:
                    x1,y1,x2,y2=[int(v) for v in xyxy]
                    color=lane_colors.get(lane.carril,(180,180,180)) if lane else (180,180,180)
                    name=lane.carril if lane else ('Calibrando' if not ready else 'Fuera de zona - no cuenta' if any(l.polygon for l in counter.lanes) else 'detectado')
                    cv2.rectangle(preview,(x1,y1),(x2,y2),color,2)
                    cv2.putText(preview,f'{mapping.get(cls,"vehiculo")} #{tid} | {name}',
                                (x1,max(16,y1-5)),cv2.FONT_HERSHEY_SIMPLEX,.5,color,2)
                if automatic:
                    status=(f'AUTO: {len(counter.lanes)} carriles | R: recalibrar' if ready else
                            f'CALIBRANDO {now_tick-calibration_start:.0f}s - esperando trayectorias estables')
                    cv2.rectangle(preview,(0,0),(w,35),(0,0,0),-1)
                    cv2.putText(preview,status,(8,24),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,255,255),1)
                for i,lane in enumerate(counter.lanes if controls.show_lanes else []):
                    color=[(0,220,255),(0,255,100),(255,180,0),(255,100,200)][i%4]
                    pixel=lambda p:(int(p[0]*w),int(p[1]*h))
                    if lane.polygon:
                        pts=np.array([pixel(p) for p in lane.polygon],dtype=np.int32)
                        cv2.polylines(preview,[pts],True,color,2)
                    cv2.line(preview,pixel(lane.a),pixel(lane.b),color,3)
                    if lane.direction!='both':
                        a=np.asarray(lane.a);b=np.asarray(lane.b);middle=(a+b)/2
                        normal=np.array([-(b-a)[1],(b-a)[0]])
                        normal=normal/max(float(np.linalg.norm(normal)),1e-8)*.025
                        if lane.direction=='positive_to_negative':normal=-normal
                        cv2.arrowedLine(preview,pixel(middle-normal),pixel(middle+normal),color,2,tipLength=.4)
                    total=sum(totals.get((lane.acceso,lane.carril,clase),0) for clase in ['auto','micro','moto'])
                    sense='+' if lane.direction=='negative_to_positive' else '-' if lane.direction=='positive_to_negative' else '+/-'
                    cv2.putText(preview,f'{lane.carril} ({sense}): {total}',pixel(lane.a),cv2.FONT_HERSHEY_SIMPLEX,.65,color,2)
                fps=n/max(time.monotonic()-preview_started,.001)
                quality=f'Captura: {w}x{h} | YOLO: {track_options["imgsz"]} | {fps:.1f} FPS'
                if c.get('crop_to_lanes',False):quality+=' | ROI carriles'
                if inference is not None and inference.elapsed_ms is not None:
                    quality+=f' | IA: {inference.elapsed_ms:.0f}ms'
                if getattr(cap,'delivered_at',None) is not None:
                    quality+=f' | cuadro: {max(0,time.monotonic()-cap.delivered_at)*1000:.0f}ms'
                preview=controls.render(preview,counter.lanes,totals,quality,
                    c.get('camera_name',c.get('source',0)),automatic,ready,cv2)
                if n==1:cv2.resizeWindow(window,preview.shape[1],preview.shape[0])
                cv2.imshow(window,preview)
                key=cv2.waitKey(1) & 0xFF
                controls.key(key,automatic)
                recalibrate=automatic and controls.recalibrate
                controls.recalibrate=False
                self.edit_requested=controls.edit
                stop=controls.stop or controls.edit or cv2.getWindowProperty(window,cv2.WND_PROP_VISIBLE)<1
                del preview
            del results,boxes,frame
            if ready and (now_tick-tick>=seconds or recalibrate) and now_tick>tick:
                end=wall(now_tick)
                yield from flush(end)
                counter.reset_interval();start=end;tick=now_tick
            if recalibrate:
                auto=AutoLanes(c.get('acceso_auto','N'));counter=LineCounter([])
                ready=False;candidate=[];stable=0;last_attempt=None;totals={};cached_labels=[]
                calibration_start=now_tick;tick=now_tick;start=wall(tick)
                print('Recalibrando: se reinician los totales de pantalla; CSV anterior conservado.',flush=True)
            if stop:break
        # Al detener o al EOF no fabricar ceros para un intervalo completo. Publicar solo el tramo efectivamente observado.
        end=wall(clock(n))
        if ready and n>0 and 0<(end-start).total_seconds()<=30.5:
            yield from flush(end)

def main():
    import yaml
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True)
    p.add_argument('--salida-conteos',type=Path,required=True,help='CSV agregado; nunca imágenes')
    p.add_argument('--inicio-video',type=datetime.fromisoformat,default=None,
      help='Solo con un archivo de video: hora real de inicio de la grabación con zona (2026-10-31T07:00:00-04:00). '
           'Los intervalos siguen el tiempo del video y no el de la PC.')
    p.add_argument('--stop-file',type=Path,help='Archivo de parada cooperativa para el gestor en segundo plano')
    p.add_argument('--auto-carriles',action='store_true',help='Aprender carriles de trayectorias antes de contar')
    p.add_argument('--calibracion-s',type=float,default=None,help='Tiempo minimo de observacion antes de estimar carriles')
    a=p.parse_args();config=yaml.safe_load(a.config.read_text(encoding='utf-8'))
    if a.stop_file:config['stop_file']=str(a.stop_file.resolve())
    if a.auto_carriles:config['auto_carriles']=True
    if a.calibracion_s is not None:config['calibracion_s']=a.calibracion_s
    if not config.get('auto_carriles') and not config.get('configuracion_verificada',False):p.error('Adaptar y verificar líneas/fuente y marcar configuracion_verificada=true')
    source=CameraSource(config,a.inicio_video)
    a.salida_conteos.parent.mkdir(parents=True,exist_ok=True)
    exists=a.salida_conteos.exists() and a.salida_conteos.stat().st_size>0
    with a.salida_conteos.open('a',encoding='utf-8',newline='') as out,Publisher('cysa-deteccion') as pub,QueuedPublisher(pub) as delivery:
        writer=None
        try:
            for event in source.eventos():
                row=event.model_dump(mode='json')
                if writer is None:
                    writer=csv.DictWriter(out,fieldnames=list(row))
                    if not exists:writer.writeheader()
                # El CSV permite reintentar un evento con el mismo UUID si el broker no confirma.
                writer.writerow(row);out.flush();delivery.publish(event)
                print(f'[{datetime.now().strftime("%H:%M:%S")}] Conteo registrado y encolado -> {event.clase}: {event.cantidad} ({event.acceso}/{event.carril})')
        except KeyboardInterrupt:pass
    # La cámara y MQTT ya están cerrados antes de abrir el editor en el gestor.
    if source.edit_requested:return 20
    return 0
if __name__=='__main__':raise SystemExit(main())
