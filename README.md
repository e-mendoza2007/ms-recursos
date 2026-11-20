# ms-recursos

Microservicio de Recursos (personas del equipo) y Asignaciones a proyectos del SaaS PPM.

## Despliegue

1. Desplegados antes: `ms-auth`, `ms-proyectos` y `ms-presupuestos`
   (Recursos lee `t_tokens_acceso` y `t_proyectos` directo (sin invocar Lambdas), y se suscribe a
   `cola-presupuestos-asignaciones`).
2. `serverless deploy`

Crea: 2 Lambdas, tablas `t_recursos` y `t_asignaciones` (GSI por proyecto y por recurso),
tema SNS `tema-recursos` y la suscripcion de `cola-presupuestos-asignaciones` a ese tema.

## Rutas (todas piden la cabecera `Authorization`)

| Ruta | Lambda | Cuerpo |
| --- | --- | --- |
| POST /recursos/crear | Recursos (`recursos.py`) | nombre, costo_hora, rol?, capacidad_semanal? |
| POST /recursos/listar | Recursos (`recursos.py`) | rol?, limit?, last_key? |
| POST /recursos/buscar | Recursos (`recursos.py`) | recurso_id |
| PUT /recursos/modificar | Recursos (`recursos.py`) | recurso_id + nombre/rol/costo_hora/capacidad_semanal |
| DELETE /recursos/eliminar | Recursos (`recursos.py`) | recurso_id |
| POST /asignaciones/crear | Asignaciones (`asignaciones.py`) | proyecto_id, recurso_id, horas |
| POST /asignaciones/listar | Asignaciones (`asignaciones.py`) | proyecto_id? o recurso_id?, limit?, last_key? |
| DELETE /asignaciones/eliminar | Asignaciones (`asignaciones.py`) | asignacion_id |

## Reglas

- `EliminarRecurso` responde 409 si el recurso ya tiene asignaciones. Para borrarlo, primero se quitan sus asignaciones con `/asignaciones/eliminar`.
- La asignacion guarda el `costo_hora` del momento y `costo = horas x costo_hora`.
  Si despues cambia el costo_hora del recurso, las asignaciones viejas no cambian.
- Capacidad semanal: se guarda pero no se valida al asignar (decision pendiente del grupo).

## Eventos

Publica `AsignacionCreada` y `AsignacionEliminada` en `tema-recursos` con `proyecto_id`, `recurso_id`, `horas` y `costo`.
Presupuestos suma el costo al crear y lo descuenta al eliminar.
`ProcesarAsignaciones` (en ms-presupuestos) lo consume y suma el costo a `costo_proyectado`.

## Prueba rapida

1. Login y poner el token en `Authorization`.
2. `POST /recursos/crear` con `{"nombre": "Ana Torres", "rol": "Desarrolladora", "costo_hora": 50, "capacidad_semanal": 40}`.
3. Tener un proyecto con presupuesto (`POST /presupuestos/crear` en ms-presupuestos).
4. `POST /asignaciones/crear` con `{"proyecto_id": "<id>", "recurso_id": "<id>", "horas": 10}`.
5. `POST /presupuestos/buscar`: `costo_proyectado` = 500 (unos segundos despues).

## Estructura de Lambdas (2)

Una Lambda atiende varios endpoints: el codigo elige la funcion segun la ruta (`requestPath` de API Gateway).

- `recursos.py` -> Lambda **Recursos**: /recursos/crear, /recursos/listar, /recursos/buscar, /recursos/modificar, /recursos/eliminar
- `asignaciones.py` -> Lambda **Asignaciones**: /asignaciones/crear, /asignaciones/listar, /asignaciones/eliminar

`comun.py` es codigo compartido (token, respuestas, helpers), no es una Lambda.
