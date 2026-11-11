from boto3.dynamodb.conditions import Key
from comun import dynamodb, NO_AUTORIZADO, respuesta, autenticar

def lambda_handler(event, context):
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
