from comun import dynamodb, NO_AUTORIZADO, respuesta, autenticar, numero_positivo

TEXTOS = ['nombre', 'rol']
NUMEROS = ['costo_hora', 'capacidad_semanal']

def lambda_handler(event, context):
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
