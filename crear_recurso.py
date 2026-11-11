import uuid
from datetime import datetime
from comun import dynamodb, NO_AUTORIZADO, respuesta, autenticar, numero_positivo

def lambda_handler(event, context):
    # Proteger el Lambda
    sesion = autenticar(event)
    if not sesion:
        return NO_AUTORIZADO
    tenant_id = sesion['tenant_id']
    # Entrada (json)
    body = event.get('body') or {}
    nombre = body.get('nombre')
    costo_hora = numero_positivo(body.get('costo_hora'))
    if not nombre or costo_hora is None:
        return respuesta(400, mensaje='Falta nombre o costo_hora (numero mayor a 0)')
    # Proceso
    recurso = {
        'tenant_id': tenant_id,
        'recurso_id': f'REC-{tenant_id}-{uuid.uuid4().hex[:8]}',
        'nombre': nombre,
        'rol': body.get('rol', ''),
        'costo_hora': costo_hora,
        'creado_en': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    if body.get('capacidad_semanal') not in (None, ''):
        capacidad = numero_positivo(body['capacidad_semanal'])
        if capacidad is None:
            return respuesta(400, mensaje='capacidad_semanal debe ser un numero mayor a 0')
        recurso['capacidad_semanal'] = capacidad
    dynamodb.Table('t_recursos').put_item(
        Item=recurso, ConditionExpression='attribute_not_exists(tenant_id)')
    # Salida (json)
    return respuesta(200, recurso=recurso)
