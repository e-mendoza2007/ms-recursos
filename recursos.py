# Lambda Recursos (ms-recursos). Una sola Lambda atiende varios endpoints.
# API Gateway (integration: lambda) manda en "requestPath" la ruta del recurso.
import uuid
from boto3.dynamodb.conditions import Key, Attr
from comun import dynamodb, NO_AUTORIZADO, respuesta, autenticar, numero_positivo, parametros_lista
from datetime import datetime


def crear_recurso(event, context):
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


def listar_recursos(event, context):
    # Proteger el Lambda
    sesion = autenticar(event)
    if not sesion:
        return NO_AUTORIZADO
    tenant_id = sesion['tenant_id']
    # Entrada (json): rol, limit y last_key son opcionales
    body = event.get('body') or {}
    # Proceso
    kwargs = parametros_lista(body)
    kwargs['KeyConditionExpression'] = Key('tenant_id').eq(tenant_id)
    if body.get('rol'):
        # Filtro aplicado despues de leer: una pagina puede traer menos items que limit
        kwargs['FilterExpression'] = Attr('rol').eq(body['rol'])
    r = dynamodb.Table('t_recursos').query(**kwargs)
    # Salida (json)
    return respuesta(200, items=r['Items'], count=r['Count'],
                     last_key=r.get('LastEvaluatedKey'))


def buscar_recurso(event, context):
    # Proteger el Lambda
    sesion = autenticar(event)
    if not sesion:
        return NO_AUTORIZADO
    tenant_id = sesion['tenant_id']
    # Entrada (json)
    recurso_id = (event.get('body') or {}).get('recurso_id')
    if not recurso_id:
        return respuesta(400, mensaje='Falta recurso_id')
    # Proceso
    r = dynamodb.Table('t_recursos').get_item(
        Key={'tenant_id': tenant_id, 'recurso_id': recurso_id})
    # Salida (json)
    if 'Item' not in r:
        return respuesta(404, mensaje='El recurso no existe')
    return respuesta(200, recurso=r['Item'])


TEXTOS = ['nombre', 'rol']


NUMEROS = ['costo_hora', 'capacidad_semanal']


def modificar_recurso(event, context):
    # Proteger el Lambda
    sesion = autenticar(event)
    if not sesion:
        return NO_AUTORIZADO
    tenant_id = sesion['tenant_id']
    # Entrada (json)
    body = event.get('body') or {}
    recurso_id = body.get('recurso_id')
    cambios = {c: body[c] for c in TEXTOS if body.get(c)}
    for c in NUMEROS:
        if body.get(c) not in (None, ''):
            n = numero_positivo(body[c])
            if n is None:
                return respuesta(400, mensaje=f'{c} debe ser un numero mayor a 0')
            cambios[c] = n
    if not recurso_id or not cambios:
        return respuesta(400, mensaje='Falta recurso_id o algun campo a modificar')
    # Proceso (las asignaciones ya creadas conservan el costo_hora con que se crearon)
    nombres, valores, partes = {}, {}, []
    for i, (campo, valor) in enumerate(cambios.items()):
        nombres[f'#c{i}'] = campo
        valores[f':v{i}'] = valor
        partes.append(f'#c{i} = :v{i}')
    try:
        r = dynamodb.Table('t_recursos').update_item(
            Key={'tenant_id': tenant_id, 'recurso_id': recurso_id},
            UpdateExpression='SET ' + ', '.join(partes),
            ConditionExpression='attribute_exists(tenant_id)',
            ExpressionAttributeNames=nombres,
            ExpressionAttributeValues=valores,
            ReturnValues='ALL_NEW'
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return respuesta(404, mensaje='El recurso no existe')
    # Salida (json)
    return respuesta(200, recurso=r['Attributes'])


def eliminar_recurso(event, context):
    # Proteger el Lambda
    sesion = autenticar(event)
    if not sesion:
        return NO_AUTORIZADO
    tenant_id = sesion['tenant_id']
    # Entrada (json)
    recurso_id = (event.get('body') or {}).get('recurso_id')
    if not recurso_id:
        return respuesta(400, mensaje='Falta recurso_id')
    # Proceso: un recurso con asignaciones no se puede borrar (quedarian asignaciones huerfanas)
    r = dynamodb.Table('t_asignaciones').query(
        IndexName='gsi_recurso',
        KeyConditionExpression=Key('tenant_id').eq(tenant_id) & Key('recurso_id').eq(recurso_id),
        Limit=1
    )
    if r['Count'] > 0:
        return respuesta(409, mensaje='El recurso tiene asignaciones y no se puede eliminar')
    try:
        dynamodb.Table('t_recursos').delete_item(
            Key={'tenant_id': tenant_id, 'recurso_id': recurso_id},
            ConditionExpression='attribute_exists(tenant_id)'
        )
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        return respuesta(404, mensaje='El recurso no existe')
    # Salida (json)
    return respuesta(200, mensaje='Recurso eliminado')


RUTAS = {
    '/recursos/crear': crear_recurso,
    '/recursos/listar': listar_recursos,
    '/recursos/buscar': buscar_recurso,
    '/recursos/modificar': modificar_recurso,
    '/recursos/eliminar': eliminar_recurso,
}

def lambda_handler(event, context):
    ruta = (event or {}).get('requestPath')
    funcion = RUTAS.get(ruta)
    if funcion is None:
        return {'statusCode': 404, 'mensaje': 'Ruta no encontrada: %s' % ruta}
    return funcion(event, context)
