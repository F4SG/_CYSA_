// La autorización sola no acredita ejecución ni una conexión física vigente.
export function integrationState(session, target, plans, board, now = Date.now()) {
    if (board?.detenido && board.sesion === session.id && board.puerto === session.port)
        return {kind:'stopped', text:'Arduino detenido por el usuario. Los rojos quedan intermitentes; pulsa Reanudar Arduino en el lanzador para continuar.'};
    const age = now - Date.parse(board?.timestamp);
    const live = Boolean(board?.activo && board.sesion === session.id && board.puerto === session.port
        && Number.isFinite(age) && age >= -1000 && age <= 3000);
    if (!live) return {kind: 'offline', text: 'Sin reporte reciente del Arduino de esta sesión. No se puede confirmar la aplicación.'};
    if (board.fase_actual === 'INTERMITENTE')
        return {kind: 'error', text: 'El MMU reportó una falla. Observa el rojo intermitente y revisa el registro del lanzador.'};
    if (board.estado_controlador !== 'conectado')
        return {kind: 'offline', text: 'Arduino en modo local; esperando conexión con el centro.'};
    if (!target) return {kind: 'ready', text: 'Arduino conectado. Elige una propuesta validada y autorízala con MFA.'};
    const plan = plans.find(row => row.id === target.id);
    if (['rechazado', 'caducado'].includes(plan?.estado_envio))
        return {kind: 'error', text: 'El plan no se aplicó: ' + (plan.detalle_envio || plan.estado_envio)};
    if (plan?.estado_envio === 'aplicado' && board.plan_activo === target.plan)
        return {kind: 'applied', text: 'Plan aplicado: recibo del controlador y plan activo coinciden. Compara las luces indicadas con los LEDs.'};
    if (plan?.estado_envio === 'aplicado')
        return {kind: 'changed', text: 'Existe un recibo de aplicación, pero ahora está activo otro plan. Revisa el plan actual.'};
    return {kind: 'waiting', text: 'Autorización registrada. Esperando envío y confirmación tras una transición segura (ámbar y todo rojo).'};
}
