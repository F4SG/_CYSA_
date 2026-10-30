"""Visor completo con panel inferior; no modifica captura, inferencia ni conteos."""

class PreviewControls:
    def __init__(self,size=None):
        self.show_lanes=True
        self.show_data=True
        self.stop=False
        self.recalibrate=False
        self.edit=False
        self.buttons=[]
        self.size=size or opening_size()

    def action(self,action):
        if action=='lanes':self.show_lanes=not self.show_lanes
        elif action=='data':self.show_data=not self.show_data
        elif action=='edit':self.edit=True
        elif action=='stop':self.stop=True
        elif action=='recalibrate':self.recalibrate=True

    def click(self,event,x,y,flags,param):
        # EVENT_LBUTTONDOWN = 1; coordenadas de imagen que OpenCV adapta al redimensionar.
        if event==1:
            for action,(left,top,right,bottom) in self.buttons:
                if left<=x<right and top<=y<bottom:
                    self.action(action)
                    break

    def key(self,key,automatic=False):
        if key==ord('l'):self.action('lanes')
        elif key==ord('d'):self.action('data')
        elif key in (ord('q'),27):self.action('stop')
        elif key==ord('e'):self.action('edit')
        elif key==ord('r') and automatic:self.action('recalibrate')

    def render(self,frame,lanes,totals,quality,camera,automatic,ready,cv2):
        import math
        import numpy as np
        width,height=self.size
        compact=width<850
        columns=max(1,width//360)
        rows=max(1,math.ceil(len(lanes)/columns))
        button_columns=2 if compact else (5 if automatic else 4)
        button_rows=math.ceil((5 if automatic else 4)/button_columns)
        button_area=button_rows*50+12
        def wrap(value,size=.57):
            lines=['']
            for word in str(value).split():
                candidate=(lines[-1]+' '+word).strip()
                if cv2.getTextSize(candidate,cv2.FONT_HERSHEY_SIMPLEX,size,1)[0][0]>width-32 and lines[-1]:lines.append(word)
                else:lines[-1]=candidate
            return lines
        quality_lines=wrap(quality,.50 if compact else .57)
        data_height=46+28*len(lanes) if compact else rows*62
        panel_height=138+24*len(quality_lines)+data_height+button_area
        video_height=max(100,height-panel_height)
        height=video_height+panel_height
        canvas=np.zeros((height,width,3),dtype=frame.dtype)
        # Solo se escala para mostrar: el modelo y los carriles usan el cuadro original.
        h,w=frame.shape[:2]
        scale=min(width/w,video_height/h)
        vw,vh=max(1,round(w*scale)),max(1,round(h*scale))
        video=cv2.resize(frame,(vw,vh),interpolation=cv2.INTER_AREA if scale<1 else cv2.INTER_LINEAR)
        x,y=(width-vw)//2,(video_height-vh)//2
        self.video_rect=(x,y,vw,vh)
        canvas[y:y+vh,x:x+vw]=video
        canvas[video_height:]=(30,30,30)
        def text(value,x,y,color=(240,240,240),size=.60,bold=False):
            cv2.putText(canvas,str(value),(x,y),cv2.FONT_HERSHEY_SIMPLEX,size,color,2 if bold else 1,cv2.LINE_AA)
        top=video_height
        status='Via inferior | contando' if ready else 'Calibrando: aun no cuenta'
        text('CYSA | '+status,16,top+28,(0,230,255),.58 if compact else .68,True)
        name=str(camera).encode('ascii','replace').decode('ascii')
        # Fuente en su propia fila y ajustada al ancho disponible.
        while cv2.getTextSize(name,cv2.FONT_HERSHEY_SIMPLEX,.57,1)[0][0]>width-32:name=name[:-4]+'...'
        text(name,16,top+54,size=.57)
        for i,line in enumerate(quality_lines):text(line,16,top+80+i*24,size=.50 if compact else .57)
        data_top=top+92+len(quality_lines)*24
        text('ACUMULADOS DE ESTA EJECUCION' if self.show_data else 'Datos ocultos [D para mostrar]',16,data_top,(0,230,255),.51 if compact else .59,True)
        if self.show_data and compact:
            positions=[16,int(width*.26),int(width*.44),int(width*.62),int(width*.81)]
            for x,label in zip(positions,['Carril','Auto','Micro','Moto','Total']):text(label,x,data_top+28,size=.51,bold=True)
            for i,lane in enumerate(lanes):
                counts=[totals.get((lane.acceso,lane.carril,cls),0) for cls in ('auto','micro','moto')]
                for x,value in zip(positions,[lane.carril,*counts,sum(counts)]):text(value,x,data_top+56+i*28,size=.57)
        elif self.show_data:
            cell_width=width//columns
            for i,lane in enumerate(lanes):
                x=16+(i%columns)*cell_width;y=data_top+28+(i//columns)*62
                counts=[totals.get((lane.acceso,lane.carril,cls),0) for cls in ('auto','micro','moto')]
                text(f'{lane.carril} | Total: {sum(counts)}',x,y,size=.64,bold=True)
                text(f'Auto {counts[0]}   Micro {counts[1]}   Moto {counts[2]}',x,y+24,size=.57)
        entries=[('lanes',f'Carriles {"SI" if self.show_lanes else "NO"} [L]'),
                 ('data',f'Datos {"SI" if self.show_data else "NO"} [D]')]
        entries.append(('edit','Editar carriles [E]'))
        if automatic:entries.append(('recalibrate','Recalibrar [R]'))
        entries.append(('stop','Detener [Q/Esc]'))
        self.buttons=[]
        gap=12;button_width=(width-gap*(button_columns+1))//button_columns
        for i,(action,label) in enumerate(entries):
            left=gap+(i%button_columns)*(button_width+gap);top=height-button_area+(i//button_columns)*50
            rect=(left,top,left+button_width,top+42)
            self.buttons.append((action,rect))
            cv2.rectangle(canvas,rect[:2],rect[2:],(65,65,65),-1)
            text(label,left+10,top+28,size=.51 if compact else .57,bold=True)
        return canvas


def fit_opening_size(work_width,work_height):
    """Ventana vertical dentro de media pantalla, reservando bordes y título."""
    height=min(900,max(240,work_height-90))
    width=min(720,max(1,work_width//2-24),int(height*.78))
    return width,height


def opening_size():
    """Tamaño inicial que deja espacio para barra de título y barra de tareas."""
    try:
        import ctypes
        from ctypes import wintypes
        area=wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(48,0,ctypes.byref(area),0):
            return fit_opening_size(area.right-area.left,area.bottom-area.top)
    except (AttributeError,OSError):pass
    return 620,820
