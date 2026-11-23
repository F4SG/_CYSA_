import copy
import pytest
from operacion.planes import huella, referencia
from cysa_controlador.reanudacion import validar_reanudacion


def confirmado():
    doc = referencia()
    doc['modo'] = 'webster'
    return dict(documento=doc, validacion={'aprobada':True,'huella_plan':huella(doc)},
                estado='autorizado', accion='autorizar', estado_envio='aplicado',
                mfa={'acr':'2','amr':['otp']}, payload={'mfa_verificado':True,'huella_plan':huella(doc)})


def test_reanudar_recupera_las_duraciones_del_plan_confirmado():
    row = confirmado()
    plan = validar_reanudacion(row, 'DEMO_FIJO')
    assert plan.plan_id == 'DEMO_FIJO'
    assert plan.fases[0].duracion_s == 30


@pytest.mark.parametrize('field,value', [('estado','validado'),('accion','rechazar'),
    ('estado_envio','enviado'),('mfa',{'amr':['pwd']}),('validacion',{'aprobada':False}),
    ('payload',{'mfa_verificado':False})])
def test_reanudar_no_activa_propuestas_sin_confirmacion_o_mfa(field, value):
    row = confirmado(); row[field] = value
    with pytest.raises(ValueError): validar_reanudacion(row, 'DEMO_FIJO')


def test_reanudar_rechaza_modificaciones_y_prioridad_temporal():
    row = confirmado(); row['documento']['verdes']['NS'] = 31
    with pytest.raises(ValueError): validar_reanudacion(row, 'DEMO_FIJO')
    row = confirmado(); row['documento']['modo'] = 'emergencia'
    with pytest.raises(ValueError): validar_reanudacion(row, 'DEMO_FIJO')
