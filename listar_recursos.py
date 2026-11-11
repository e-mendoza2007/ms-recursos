from boto3.dynamodb.conditions import Key, Attr
from comun import dynamodb, NO_AUTORIZADO, respuesta, autenticar, parametros_lista

def lambda_handler(event, context):
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
