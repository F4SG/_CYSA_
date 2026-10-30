from types import SimpleNamespace
import cv2
import numpy as np
from cysa_detector.preview import PreviewControls,fit_opening_size


def test_vista_completa_sin_recortar_tapar_o_alterar_datos():
    frame=np.full((720,1280,3),107,np.uint8)
    original=frame.copy()
    lane=SimpleNamespace(acceso='N',carril='N_0')
    totals={('N','N_0','moto'):7}
    controls=PreviewControls(size=(1280,1010))
    canvas=controls.render(frame,[lane],totals,'Captura: 1280x720 | ROI carriles','S10+',False,True,cv2)
    assert canvas.shape==(1010,1280,3)
    x,y,w,h=controls.video_rect
    assert np.array_equal(canvas[y:y+h,x:x+w],cv2.resize(original,(w,h),interpolation=cv2.INTER_AREA))
    assert np.array_equal(frame,original)
    assert totals=={('N','N_0','moto'):7}
    for _,(left,top,right,bottom) in controls.buttons:
        assert top>=y+h and 0<=left<right<=1280 and bottom<=canvas.shape[0]


def test_clicks_y_teclas_solo_cambian_visualizacion_o_piden_cierre():
    controls=PreviewControls()
    controls.render(np.zeros((480,640,3),np.uint8),[],{},'30 FPS','S10+',False,True,cv2)
    rect=controls.buttons[0][1]
    controls.click(1,rect[0]+1,rect[1]+1,0,None)
    assert not controls.show_lanes
    controls.key(ord('l'))
    controls.key(ord('d'))
    assert controls.show_lanes and not controls.show_data
    controls.click(1,10,10,0,None)
    assert not controls.stop
    controls.key(ord('q'))
    assert controls.stop


def test_recalibrar_se_ofrece_solo_en_modo_automatico():
    controls=PreviewControls()
    frame=np.zeros((480,640,3),np.uint8)
    controls.render(frame,[],{},'','S10+',False,True,cv2)
    assert 'recalibrate' not in dict(controls.buttons)
    controls.key(ord('r'),False)
    assert not controls.recalibrate
    controls.render(frame,[],{},'','S10+',True,True,cv2)
    assert 'recalibrate' in dict(controls.buttons)
    controls.key(ord('r'),True)
    assert controls.recalibrate


def test_panel_inferior_cabe_en_apertura_de_portatil():
    controls=PreviewControls(size=(1100,650))
    lanes=[SimpleNamespace(acceso='N',carril=f'N_{i}') for i in range(3)]
    frame=np.full((720,1280,3),107,np.uint8)
    canvas=controls.render(frame,lanes,{},'Captura: 1280x720 | YOLO: 512 | 17.0 FPS | ROI carriles | cuadro: 78ms','Galaxy S10+ (Windows Virtual Camera)',False,True,cv2)
    assert canvas.shape==(650,1100,3)
    assert np.array_equal(frame,np.full_like(frame,107))
    assert all(bottom<=650 and left>=0 and right<=1100 for _,(left,top,right,bottom) in controls.buttons)
    assert all(top>=500 for _,(left,top,right,bottom) in controls.buttons)


def test_ventana_vertical_dentro_de_media_pantalla():
    for screen in [(1920,1040),(1366,728),(1280,680)]:
        width,height=fit_opening_size(*screen)
        assert width<height and width+24<=screen[0]//2 and height+90<=screen[1]
        controls=PreviewControls(size=(width,height))
        lanes=[SimpleNamespace(acceso='N',carril=f'N_{i}') for i in range(3)]
        canvas=controls.render(np.zeros((720,1280,3),np.uint8),lanes,{},'Captura: 1280x720 | YOLO: 512 | 17.0 FPS | ROI carriles | cuadro: 78ms','Galaxy S10+ (Windows Virtual Camera)',False,True,cv2)
        assert canvas.shape==(height,width,3)
        assert all(0<=left<right<=width and 0<=top<bottom<=height for _,(left,top,right,bottom) in controls.buttons)
        for action,rect in controls.buttons:
            label={'lanes':'Carriles SI [L]','data':'Datos SI [D]','stop':'Detener [Q/Esc]','edit':'Editar carriles [E]'}[action]
            assert cv2.getTextSize(label,cv2.FONT_HERSHEY_SIMPLEX,.51,2)[0][0]+20<=rect[2]-rect[0]


def test_editar_no_borra_datos_ni_solicita_cierre_definitivo():
    controls=PreviewControls(size=(620,820))
    controls.render(np.zeros((720,1280,3),np.uint8),[],{},'','S10+',False,True,cv2)
    rect=dict(controls.buttons)['edit']
    controls.click(1,rect[0]+1,rect[1]+1,0,None)
    assert controls.edit and not controls.stop
