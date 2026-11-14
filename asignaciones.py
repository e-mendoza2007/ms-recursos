# Lambda Asignaciones (ms-recursos). Una sola Lambda atiende varios endpoints.
# API Gateway (integration: lambda) manda en "requestPath" la ruta del recurso.
import os
import uuid
from boto3.dynamodb.conditions import Key
from comun import dynamodb, NO_AUTORIZADO, respuesta, autenticar, proyecto_existe, numero_positivo, publicar, parametros_lista
from datetime import datetime


def crear_asignacion(event, context):
    # Proteger el Lambda
    sesion = autenticar(event)
    if not sesion:
        return NO_AUTORIZADO
    tenant_id = sesion['tenant_id']
    # Entrada (json)
    body = event.get('body') or {}
    proyecto_id = body.get('proyecto_id')
    recurso_id = body.get('recurso_id')
    horas = numero_positivo(body.get('horas'))
    if not proyecto_id or not recurso_id or horas is None:
        return respuesta(400, mensaje='Falta proyecto_id, recurso_id o horas (numero mayor a 0)')
    # Proceso 1: el recurso es de este microservicio
    r = dynamodb.Table('t_recursos').get_item(
        Key={'tenant_id': tenant_id, 'recurso_id': recurso_id})
    if 'Item' not in r:
        return respuesta(404, mensaje='El recurso no existe')
    costo_hora = r['Item']['costo_hora']
    # Proceso 2: el proyecto es de ms-proyectos
    if not proyecto_existe(event, proyecto_id):
        return respuesta(404, mensaje='El proyecto no existe')
    # Proceso 3: se guarda la asignacion con el costo calculado (horas x costo_hora)
    asignacion = {
        'tenant_id': tenant_id,
        'asignacion_id': f'ASG-{tenant_id}-{uuid.uuid4().hex[:8]}',
        'proyecto_id': proyecto_id,
        'recurso_id': recurso_id,
        'horas': horas,
        'costo_hora': costo_hora,
        'costo': horas * costo_hora,
        'creado_en': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    dynamodb.Table('t_asignaciones').put_item(
        Item=asignacion, ConditionExpression='attribute_not_exists(tenant_id)')
    # Evento para Presupuestos (costo_proyectado)
    publicar(os.environ['TOPIC_RECURSOS_ARN'], 'AsignacionCreada', tenant_id,
             {'proyecto_id': proyecto_id, 'recurso_id': recurso_id,
              'asignacion_id': asignacion['asignacion_id'],
              'horas': horas, 'costo': asignacion['costo']})
    # Salida (json)
    return respuesta(200, asignacion=asignacion)


def listar_asignaciones(event, context):
    # Proteger el Lambda
    sesion = autenticar(event)
    if not sesion:
        return NO_AUTORIZADO
    tenant_id = sesion['tenant_id']
    # Entrada (json): proyecto_id o recurso_id (opcionales), limit y last_key
    body = event.get('body') or {}
    # Proceso
    kwargs = parametros_lista(body)
    if body.get('proyecto_id'):
        kwargs['IndexName'] = 'gsi_proyecto'
        kwargs['KeyConditionExpression'] = Key('tenant_id').eq(tenant_id) & Key('proyecto_id').eq(body['proyecto_id'])
    elif body.get('recurso_id'):
        kwargs['IndexName'] = 'gsi_recurso'
        kwargs['KeyConditionExpression'] = Key('tenant_id').eq(tenant_id) & Key('recurso_id').eq(body['recurso_id'])
    else:
        kwargs['KeyConditionExpression'] = Key('tenant_id').eq(tenant_id)
    r = dynamodb.Table('t_asignaciones').query(**kwargs)
    # Salida (json)
    return respuesta(200, items=r['Items'], count=r['Count'],
                     last_key=r.get('LastEvaluatedKey'))


RUTAS = {
    '/asignaciones/crear': crear_asignacion,
    '/asignaciones/listar': listar_asignaciones,
}

def lambda_handler(event, context):
    ruta = (event or {}).get('requestPath')
    funcion = RUTAS.get(ruta)
    if funcion is None:
        return {'statusCode': 404, 'mensaje': 'Ruta no encontrada: %s' % ruta}
    return funcion(event, context)
