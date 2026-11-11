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
    # Proceso
    r = dynamodb.Table('t_recursos').get_item(
        Key={'tenant_id': tenant_id, 'recurso_id': recurso_id})
    # Salida (json)
    if 'Item' not in r:
        return respuesta(404, mensaje='El recurso no existe')
    return respuesta(200, recurso=r['Item'])
