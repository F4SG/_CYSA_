"""Recupera exclusivamente un plan persistido como autorizado con MFA y aplicado."""
from operacion.planes import huella, validar
from operacion.sqlserver import connection


def recuperar_plan(plan_id, conectar=connection):
    with conectar() as db:
        row = db.execute('''SELECT p.documento,p.validacion,p.estado,d.accion,d.mfa,
            e.estado AS estado_envio,e.payload FROM control_planes p
            JOIN control_decisiones d ON d.plan_id=p.id
            JOIN control_envios e ON e.solicitud_id=d.solicitud_id
            WHERE JSON_VALUE(p.documento,'$.plan_id')=%s''', (plan_id,)).fetchone()
    return validar_reanudacion(row, plan_id)


def validar_reanudacion(row, plan_id):
    if not row or row['estado'] != 'autorizado' or row['accion'] != 'autorizar' or row['estado_envio'] != 'aplicado':
        raise ValueError('Solo se puede reanudar un plan autorizado y con aplicación confirmada')
    doc, validation, mfa = row['documento'], row['validacion'], row['mfa']
    payload = row['payload']
    if doc['plan_id'] != plan_id or doc['modo'] == 'emergencia':
        raise ValueError('No se reanudan prioridades temporales de emergencia')
    if not validation.get('aprobada') or validation.get('huella_plan') != huella(doc):
        raise ValueError('El plan guardado no coincide con la versión validada')
    if not mfa or not (mfa.get('acr') == '2' or set(mfa.get('amr', [])) & {'otp','mfa','hwk'}):
        raise ValueError('El plan no tiene evidencia de autorización MFA')
    if payload.get('mfa_verificado') is not True or payload.get('huella_plan') != huella(doc):
        raise ValueError('La orden original no coincide con el plan confirmado')
    return validar(doc)[1]
