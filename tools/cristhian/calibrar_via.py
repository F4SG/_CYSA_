"""Calibración de una sola vía por cuatro esquinas, sin guardar cuadros."""
import argparse,math,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'deteccion'))
from cysa_detector.preview import opening_size

def create_lanes(points,count,access='N',direction='both',line_at=.6):
    import cv2,numpy as np
    from cysa_detector.counter import Lane,cross
    if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=8:
        raise ValueError('Elegir entre 1 y 8 carriles')
    if len(points)!=4 or any(len(p)!=2 or any(not math.isfinite(v) or not 0<=v<=1 for v in p) for p in points):
        raise ValueError('Marcar cuatro esquinas normalizadas dentro de la imagen')
    turns=[cross(points[i],points[(i+1)%4],points[(i+2)%4]) for i in range(4)]
    if not (all(t>1e-8 for t in turns) or all(t< -1e-8 for t in turns)):
        raise ValueError('Las esquinas deben seguir el contorno sin cruzarse')
    if not 0<line_at<1:raise ValueError('La linea debe quedar dentro de la via')
    matrix=cv2.getPerspectiveTransform(np.array([[0,0],[1,0],[1,1],[0,1]],np.float32),np.asarray(points,np.float32))
    def project(x,y):
        p=matrix@np.array([x,y,1.])
        if abs(p[2])<1e-8:raise ValueError('Perspectiva degenerada; marcar nuevamente')
        return tuple(float(v) for v in np.clip(p[:2]/p[2],0,1))
    lanes=[]
    for i in range(count):
        left,right=i/count,(i+1)/count
        polygon=tuple(project(x,y) for x,y in [(left,0),(right,0),(right,1),(left,1)])
        a,b=project(left,line_at),project(right,line_at)
        lane=Lane(access,f'{access}_{i}',a,b,direction,polygon)
        lanes.append(dict(acceso=access,carril=lane.carril,polygon=[list(p) for p in polygon],a=list(a),b=list(b),direction=direction))
    return lanes

def frame_ready(frame):
    """Descarta negro/uniforme de arranque; no acredita enfoque ni precisión."""
    import numpy as np
    if frame is None or frame.size==0:return False
    sample=frame[::max(1,frame.shape[0]//120),::max(1,frame.shape[1]//160)]
    gray=sample.mean(axis=2) if sample.ndim==3 else sample
    return bool(np.mean(gray>15)>.05 and np.percentile(gray,95)-np.percentile(gray,5)>12)

class PreviewState:
    def __init__(self):self.frame=None;self.ready=False;self.frozen=False;self.points=[]
    def update(self,frame):
        if not self.frozen and frame is not None:
            self.frame=frame;self.ready=frame_ready(frame)
    def toggle_freeze(self):
        if self.frozen:
            self.frozen=False;self.points.clear();return True
        if not self.ready:return False
        self.frame=self.frame.copy();self.frozen=True;return True

class CalibrationView:
    """Editor vertical con controles fuera del video y coordenadas reversibles."""
    def __init__(self):
        self.size=opening_size();self.rect=None;self.buttons=[];self.pending=-1
    def point(self,x,y):
        if self.rect is None:return None
        left,top,w,h=self.rect
        if left<=x<left+w and top<=y<top+h:return ((x-left)/w,(y-top)/h)
        return None
    def render(self,frame,status,count,message,cv2):
        import numpy as np
        width,height=self.size;video_height=height-320
        canvas=np.zeros((height,width,3),np.uint8)
        h,w=frame.shape[:2];scale=min(width/w,video_height/h)
        vw,vh=max(1,round(w*scale)),max(1,round(h*scale))
        x,y=(width-vw)//2,(video_height-vh)//2;self.rect=(x,y,vw,vh)
        canvas[y:y+vh,x:x+vw]=cv2.resize(frame,(vw,vh))
        canvas[video_height:]=(30,30,30)
        def text(value,y,size=.51,color=(240,240,240)):
            cv2.putText(canvas,value,(12,y),cv2.FONT_HERSHEY_SIMPLEX,size,color,1,cv2.LINE_AA)
        top=video_height
        text(status,top+25,.56,(0,230,255))
        text(f'SOLO via inferior | {count} carriles',top+50)
        text('Esquinas: lejana izq., lejana der.,',top+75)
        text('cercana der., cercana izq. | U: deshacer',top+98)
        text('+ / -: mover linea | 1-8: carriles',top+121)
        text(message[:max(20,int(width/8.5))],top+146,.46,(0,230,255))
        entries=[('Fijar / reanudar',ord(' ')),('Deshacer [U]',ord('u')),
                 ('Carril -1',ord(str(max(1,count-1)))),('Carril +1',ord(str(min(8,count+1)))),
                 ('Guardar [S]',ord('s')),('Volver [Q]',ord('q'))]
        self.buttons=[];bw=(width-36)//2
        for i,(label,key) in enumerate(entries):
            x=12+(i%2)*(bw+12);y=height-150+(i//2)*48
            rect=(x,y,x+bw,y+40);self.buttons.append((rect,key))
            cv2.rectangle(canvas,rect[:2],rect[2:],(65,65,65),-1)
            cv2.putText(canvas,label,(x+8,y+26),cv2.FONT_HERSHEY_SIMPLEX,.50,(255,255,255),1,cv2.LINE_AA)
        return canvas


def main():
    import cv2,numpy as np,yaml
    from cysa_detector.camera import open_source
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,default=ROOT/'deteccion/config/carriles_cristhian.yaml')
    p.add_argument('--carriles',type=int,default=3,help='Propuesta inicial; teclas 1-8 para corregir antes de guardar')
    p.add_argument('--acceso',default='N')
    p.add_argument('--direction',choices=['negative_to_positive','positive_to_negative','both'],default='negative_to_positive',help='Por defecto: del borde lejano al cercano')
    p.add_argument('--iniciar',action='store_true',help='Iniciar detector despues de guardar y liberar la camara')
    args=p.parse_args()
    if not 1<=args.carriles<=8:p.error('--carriles debe estar entre 1 y 8')
    config=yaml.safe_load(args.config.read_text(encoding='utf-8'))
    cap=open_source(cv2,config.get('source',1),config)
    window='CYSA - Calibrar SOLO via inferior'
    state=PreviewState();view=CalibrationView();count=args.carriles;line_at=.6;message='';saved=False;displayed=False
    cv2.namedWindow(window,cv2.WINDOW_NORMAL)
    def click(event,x,y,*unused):
        nonlocal message
        if event!=cv2.EVENT_LBUTTONDOWN:return
        for rect,key in view.buttons:
            if rect[0]<=x<rect[2] and rect[1]<=y<rect[3]:view.pending=key;return
        if not state.frozen:
            message='Primero fija la imagen con ESPACIO';return
        point=view.point(x,y)
        if point is not None and len(state.points)<4:state.points.append(point)
    cv2.setMouseCallback(window,click)
    print('Via inferior: esquina lejana izquierda, lejana derecha, cercana derecha, cercana izquierda.',flush=True)
    print('ESPACIO: fijar/reanudar imagen. Incluir solo asfalto de esa via. 1-8: cantidad; U: deshacer; +/-: mover linea; S: guardar; Q: cancelar.',flush=True)
    try:
        while True:
            # Mantener la captura abierta y drenada incluso al marcar sobre la imagen fija.
            ok,raw=cap.poll(.05) if hasattr(cap,'poll') else cap.read()
            if ok:
                state.update(raw)
            if state.frame is None:
                preview=np.zeros((480,850,3),dtype=np.uint8)
            else:preview=state.frame.copy()
            h,w=preview.shape[:2];points=state.points;lanes=[]
            pixel=lambda pt:(int(pt[0]*w),int(pt[1]*h))
            for i,point in enumerate(points):
                cv2.circle(preview,pixel(point),6,(0,255,255),-1)
                cv2.putText(preview,str(i+1),pixel(point),cv2.FONT_HERSHEY_SIMPLEX,.7,(255,255,255),2)
            if len(points)==4:
                try:lanes=create_lanes(points,count,args.acceso,direction=args.direction,line_at=line_at)
                except ValueError as error:message=str(error)
                for i,lane in enumerate(lanes):
                    color=[(0,255,255),(0,255,100),(255,180,0),(255,100,200)][i%4]
                    cv2.polylines(preview,[np.array([pixel(pt) for pt in lane['polygon']],np.int32)],True,color,2)
                    cv2.line(preview,pixel(lane['a']),pixel(lane['b']),color,3)
                    cv2.putText(preview,lane['carril'],pixel(lane['a']),cv2.FONT_HERSHEY_SIMPLEX,.65,color,2)
            status='IMAGEN FIJA: marca las 4 esquinas' if state.frozen else 'EN VIVO: ESPACIO para fijar' if state.ready else 'Esperando imagen del S10+'
            preview=view.render(preview,status,count,message or f'Esquinas marcadas: {len(points)}/4',cv2)
            if not displayed:
                cv2.resizeWindow(window,preview.shape[1],preview.shape[0]);displayed=True
            cv2.imshow(window,preview);key=cv2.waitKey(20)&255
            if view.pending!=-1:key=view.pending;view.pending=-1
            if key in (ord('q'),27) or cv2.getWindowProperty(window,cv2.WND_PROP_VISIBLE)<1:break
            if key==ord(' '):
                if not state.toggle_freeze():message='Todavia no hay imagen util; espera o revisa el telefono'
                else:message=''
            if ord('1')<=key<=ord('8'):count=key-ord('0');message=''
            if key==ord('u') and points:points.pop();message=''
            if key in (ord('+'),ord('=')):line_at=min(.9,line_at+.05)
            if key==ord('-'):line_at=max(.1,line_at-.05)
            if key==ord('s'):
                if not state.frozen or not lanes:message='Fija una imagen valida y marca las cuatro esquinas';continue
                config.update(lanes=lanes,auto_carriles=False,configuracion_verificada=True,show=True,show_outside_lanes=False)
                args.config.write_text(yaml.safe_dump(config,allow_unicode=True,sort_keys=False),encoding='utf-8')
                print(f'Guardados {count} carriles fijos de la via inferior. Puente excluido de conteo y recuadros.',flush=True)
                saved=True;break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    if saved and args.iniciar:
        import subprocess
        raise SystemExit(subprocess.call([sys.executable,str(ROOT/'tools/cristhian/detector.py'),'iniciar','--config',str(args.config.resolve())],cwd=ROOT))

if __name__=='__main__':main()
