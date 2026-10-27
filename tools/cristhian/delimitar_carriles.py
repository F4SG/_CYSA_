"""Marca carriles y segmentos de conteo sobre un cuadro en RAM; guarda solo YAML."""
import argparse,time,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'deteccion'))
from cysa_detector.camera import open_source

def make_lane(points,index,access,direction):
    from cysa_detector.counter import Lane,cross
    if len(points)!=6:raise ValueError('Faltan puntos: cuatro esquinas y dos extremos de linea')
    polygon=tuple(tuple(p) for p in points[:4])
    turns=[cross(polygon[i],polygon[(i+1)%4],polygon[(i+2)%4]) for i in range(4)]
    if not (all(t>1e-8 for t in turns) or all(t< -1e-8 for t in turns)):
        raise ValueError('Marca las cuatro esquinas en orden alrededor de un carril sin cruzarlas')
    lane=Lane(access,f'{access}_{index}',tuple(points[4]),tuple(points[5]),direction,polygon)
    return dict(acceso=lane.acceso,carril=lane.carril,polygon=[list(p) for p in polygon],
                a=list(lane.a),b=list(lane.b),direction=direction)

def main():
    import cv2,numpy as np,yaml
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--acceso',default='N')
    p.add_argument('--direction',choices=['both','negative_to_positive','positive_to_negative'],default='both')
    args=p.parse_args()
    config=yaml.safe_load(args.config.read_text(encoding='utf-8'))
    source=config.get('source',1)
    cap=open_source(cv2,source,config)
    try:
        deadline=time.monotonic()+10
        ok,frame=cap.read()
        while not ok and time.monotonic()<deadline:
            time.sleep(.03);ok,frame=cap.read()
        if not ok:raise SystemExit('No hay imagen. Cierra el detector antes de marcar carriles.')
    finally:cap.release()
    scale=min(1.,800/frame.shape[0],1200/frame.shape[1])
    frame=cv2.resize(frame,None,fx=scale,fy=scale)
    h,w=frame.shape[:2];points=[];lanes=[];message=''
    window='CYSA - Marcar carriles'
    cv2.namedWindow(window,cv2.WINDOW_AUTOSIZE)
    def click(event,x,y,*unused):
        if event==cv2.EVENT_LBUTTONDOWN and len(points)<6 and 0<=x<w and 0<=y<h:
            points.append((x/w,y/h))
    cv2.setMouseCallback(window,click)
    print('Por carril: 4 clics en esquinas en orden y 2 clics para la linea interior.')
    print('N: agregar carril. U: deshacer. S: guardar todos. Q/Esc: cancelar.')
    try:
        while True:
            preview=frame.copy()
            pixel=lambda point:(int(point[0]*w),int(point[1]*h))
            for lane in lanes:
                pts=np.array([pixel(point) for point in lane['polygon']],np.int32)
                cv2.polylines(preview,[pts],True,(0,255,100),2)
                cv2.line(preview,pixel(lane['a']),pixel(lane['b']),(0,255,255),3)
                cv2.putText(preview,lane['carril'],pixel(lane['a']),cv2.FONT_HERSHEY_SIMPLEX,.65,(0,255,255),2)
            for i,point in enumerate(points):
                cv2.circle(preview,pixel(point),5,(0,220,255),-1)
                cv2.putText(preview,str(i+1),pixel(point),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),2)
            if len(points)>=2:
                cv2.polylines(preview,[np.array([pixel(pt) for pt in points[:4]],np.int32)],len(points)>=4,(0,220,255),2)
            if len(points)==6:cv2.line(preview,pixel(points[4]),pixel(points[5]),(0,255,255),3)
            instruction=f'Carril {len(lanes)+1}: esquinas {min(len(points),4)}/4, linea {max(0,len(points)-4)}/2'
            cv2.rectangle(preview,(0,0),(w,72),(0,0,0),-1)
            cv2.putText(preview,instruction,(10,22),cv2.FONT_HERSHEY_SIMPLEX,.5,(255,255,255),1)
            cv2.putText(preview,'N: agregar | U: deshacer | S: guardar | Q: cancelar',(10,44),cv2.FONT_HERSHEY_SIMPLEX,.45,(255,255,255),1)
            cv2.putText(preview,message,(10,64),cv2.FONT_HERSHEY_SIMPLEX,.4,(0,220,255),1)
            cv2.imshow(window,preview)
            key=cv2.waitKey(20)&0xFF
            if key in (ord('q'),27) or cv2.getWindowProperty(window,cv2.WND_PROP_VISIBLE)<1:
                print('Cancelado: configuracion sin cambios.');return
            if key==ord('u'):
                if points:points.pop()
                elif lanes:points.extend(tuple(p) for p in lanes.pop()['polygon'])
                message=''
            if key in (ord('n'),ord('s')):
                try:
                    if points:
                        lane=make_lane(points,len(lanes),args.acceso,args.direction)
                        lanes.append(lane);points.clear();message='Carril agregado'
                    elif key==ord('n'):message='Marca primero las cuatro esquinas y la linea'
                    if key==ord('s'):
                        if not lanes:raise ValueError('Marca al menos un carril')
                        config.update(lanes=lanes,configuracion_verificada=True,show=True,auto_carriles=False)
                        args.config.write_text(yaml.safe_dump(config,allow_unicode=True,sort_keys=False),encoding='utf-8')
                        print(f'Guardados {len(lanes)} carriles en {args.config}. Puedes iniciar el detector.');return
                except ValueError as error:message=str(error);print(message)
    finally:cv2.destroyAllWindows()

if __name__=='__main__':main()
