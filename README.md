# ms-recursos

Microservicio de Recursos (personas del equipo) y Asignaciones a proyectos del SaaS PPM.

## Despliegue

1. Desplegados antes: `ms-auth`, `ms-proyectos` y `ms-presupuestos`
   (Recursos invoca `ValidarTokenAcceso` y `BuscarProyecto`, y se suscribe a
   `cola-presupuestos-asignaciones`).
2. `serverless deploy`

Crea: 7 Lambdas, tablas `t_recursos` y `t_asignaciones` (GSI por proyecto y por recurso),
tema SNS `tema-recursos` y la suscripcion de `cola-presupuestos-asignaciones` a ese tema.

## Rutas (todas piden la cabecera `Authorization`)

| Ruta | Lambda | Cuerpo |
| --- | --- | --- |
| POST /recursos/crear | CrearRecurso | nombre, costo_hora, rol?, capacidad_semanal? |
| POST /recursos/listar | ListarRecursos | rol?, limit?, last_key? |
| POST /recursos/buscar | BuscarRecurso | recurso_id |
| PUT /recursos/modificar | ModificarRecurso | recurso_id + nombre/rol/costo_hora/capacidad_semanal |
| DELETE /recursos/eliminar | EliminarRecurso | recurso_id |
| POST /asignaciones/crear | CrearAsignacion | proyecto_id, recurso_id, horas |
| POST /asignaciones/listar | ListarAsignaciones | proyecto_id? o recurso_id?, limit?, last_key? |

## Reglas

- `EliminarRecurso` responde 409 si el recurso ya tiene asignaciones.
- La asignacion guarda el `costo_hora` del momento y `costo = horas x costo_hora`.
  Si despues cambia el costo_hora del recurso, las asignaciones viejas no cambian.
- Capacidad semanal: se guarda pero no se valida al asignar (decision pendiente del grupo).

## Eventos

Publica `AsignacionCreada` en `tema-recursos` con `proyecto_id`, `recurso_id`, `horas` y `costo`.
`ProcesarAsignaciones` (en ms-presupuestos) lo consume y suma el costo a `costo_proyectado`.

## Prueba rapida

1. Login y poner el token en `Authorization`.
2. `POST /recursos/crear` con `{"nombre": "Ana Torres", "rol": "Desarrolladora", "costo_hora": 50, "capacidad_semanal": 40}`.
3. Tener un proyecto con presupuesto (`POST /presupuestos/crear` en ms-presupuestos).
4. `POST /asignaciones/crear` con `{"proyecto_id": "<id>", "recurso_id": "<id>", "horas": 10}`.
5. `POST /presupuestos/buscar`: `costo_proyectado` = 500 (unos segundos despues).
