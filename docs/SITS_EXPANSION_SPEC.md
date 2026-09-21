Quiero que trabajes directamente sobre mi aplicativo SITS y realices una ampliación estructural y funcional importante.



IMPORTANTE:

\- No quiero una aplicación nueva.

\- Debes trabajar sobre la aplicación existente.

\- Primero analiza completamente el repositorio, frontend, backend, modelos, rutas, migraciones, autenticación, permisos, componentes reutilizables, formularios existentes y estructura actual de base de datos.

\- Conserva toda la funcionalidad que actualmente funciona.

\- No elimines funcionalidades existentes.

\- Reutiliza componentes actuales siempre que sea posible.

\- No dupliques lógica innecesariamente.

\- Antes de modificar una arquitectura importante, identifica dependencias.

\- Implementa cambios de manera modular y mantenible.

\- Ejecuta tests y build antes de dar por terminado el trabajo.

\- Si encuentras código existente relacionado con una funcionalidad solicitada, extiéndelo en lugar de reemplazarlo sin necesidad.

\- Trabaja de forma autónoma. No me pidas confirmación por cada archivo.

\- Solo detente si existe un bloqueo real que requiera credenciales, una decisión empresarial que no pueda inferirse o información que no exista en el proyecto.



==================================================

1\. OBJETIVO GENERAL

==================================================



Quiero transformar SITS en un Sistema Integral de Gestión de Trabajo Social, Departamento Médico, Encuestas, Beneficios y procesos relacionados.



La aplicación debe organizarse mediante la siguiente jerarquía conceptual:



MACROPROCESO

→ SUBPROCESO

→ PROCESO

→ MÓDULO / REGISTROS / FORMULARIOS



El macroproceso principal será:



TRABAJO SOCIAL



Dentro de este macroproceso deben existir diferentes áreas y procesos.



==================================================

2\. NUEVA ESTRUCTURA DEL MENÚ

==================================================



Reestructura el sidebar para soportar menús jerárquicos, colapsables y escalables.



La estructura inicial debe ser aproximadamente:



TRABAJO SOCIAL



Inicio



Personas



Trabajo Social

&#x20;   Casos

&#x20;   Atenciones

&#x20;   Novedades

&#x20;   Recorridos

&#x20;   Formularios



Departamento Médico

&#x20;   Riesgos de Trabajo

&#x20;       Casos

&#x20;       Seguimientos

&#x20;       Formularios

&#x20;       Documentos

&#x20;       Historial



&#x20;   Ausentismo

&#x20;       Dashboard

&#x20;       Importar Excel

&#x20;       Registros

&#x20;       Indicadores

&#x20;       Historial de cargas



&#x20;   Accidentes

&#x20;       Dashboard

&#x20;       Importar Excel

&#x20;       Accidentes registrados

&#x20;       Seguimientos

&#x20;       Formularios

&#x20;       Documentos

&#x20;       Notificaciones



&#x20;   Formularios médicos



Encuestas

&#x20;   Producción

&#x20;   Operaciones

&#x20;   Oficina

&#x20;   Crear encuesta

&#x20;   Respuestas

&#x20;   Resultados



Beneficios

&#x20;   Seguros

&#x20;   Tía

&#x20;   Otros beneficios

&#x20;   Formularios de atención



Administración

&#x20;   Usuarios

&#x20;   Roles y permisos

&#x20;   Catálogos

&#x20;   Configuraciones

&#x20;   Automatizaciones

&#x20;   Auditoría



El sidebar debe:



\- Permitir expandir y contraer niveles.

\- Mantener el diseño visual actual de SITS.

\- Funcionar correctamente en desktop y móvil.

\- Mantener el sidebar colapsable actual.

\- Resaltar claramente la ruta activa.

\- Soportar futuras incorporaciones sin tener que rehacer el componente.



==================================================

3\. PERSONAS COMO MAESTRO CENTRAL

==================================================



No quiero bases diferentes de personas para cada módulo.



Debe existir una sola entidad PERSONA/COLABORADOR.



Todos los módulos deben relacionarse mediante person\_id o equivalente.



Una persona podrá tener asociados:



\- Casos.

\- Atenciones.

\- Novedades.

\- Riesgos de trabajo.

\- Accidentes.

\- Ausentismo.

\- Formularios.

\- Encuestas cuando corresponda.

\- Seguros.

\- Dependientes.

\- Beneficios.

\- Documentos.

\- Historial.



Amplía la ficha de Persona para que pueda mostrar pestañas como:



Resumen

Casos

Atenciones

Riesgos de Trabajo

Ausentismo

Accidentes

Encuestas

Seguros

Beneficios

Documentos

Historial



No cargues toda la información de todas las pestañas de golpe si afecta el rendimiento. Utiliza consultas por módulo o lazy loading cuando corresponda.



==================================================

4\. MOTOR DE FORMULARIOS

==================================================



SITS ya posee funcionalidad de formularios dinámicos.



Analiza el constructor actual y conviértelo en un MOTOR TRANSVERSAL DE FORMULARIOS.



No quiero crear componentes completamente diferentes para cada proceso.



Los formularios deben poder relacionarse con:



\- Trabajo Social.

\- Casos.

\- Riesgos de Trabajo.

\- Accidentes.

\- Ausentismo.

\- Departamento Médico.

\- Producción.

\- Operaciones.

\- Oficina.

\- Seguros.

\- Beneficios.

\- Atenciones.



Cada formulario debe poder tener:



nombre

descripción

módulo

proceso

estado

fecha de publicación

fecha de cierre

editable o no editable

activo/inactivo

preguntas

versionado

creador

fecha de creación

fecha de modificación



Mantén compatibilidad con los formularios ya existentes.



==================================================

5\. RESPUESTAS EDITABLES Y AUDITORÍA

==================================================



Quiero permitir que determinados formularios puedan modificarse después de ser enviados.



Pero NO quiero sobrescribir información sin dejar trazabilidad.



Implementa historial de versiones.



Ejemplo:



Versión 1

Creada por Usuario A

10/09/2026 10:15



Versión 2

Modificada por Usuario B

10/09/2026 14:27



Cambios:

Plan 5K → Plan 20K



Debe registrarse:



usuario

fecha/hora

acción

valor anterior

valor nuevo

entidad

registro afectado



Crear un módulo o vista de AUDITORÍA.



==================================================

6\. RIESGOS DE TRABAJO

==================================================



Dentro de Departamento Médico crea el proceso:



Riesgos de Trabajo



Debe funcionar conceptualmente parecido al módulo actual de Casos.



Un Riesgo de Trabajo debe poder tener:



Datos generales

Persona

Fecha

Tipo

Descripción

Estado

Responsable

Seguimientos

Formularios

Documentos

Historial

Observaciones



Estados inicialmente:



Abierto

En seguimiento

Pendiente

Cerrado



Usa catálogos configurables cuando sea conveniente.



==================================================

7\. AUSENTISMO

==================================================



Crear módulo de Ausentismo.



Debe permitir importar archivos Excel.



Necesito un importador robusto.



Flujo:



Subir archivo Excel

→ analizar columnas

→ mostrar previsualización

→ validar información

→ relacionar colaborador por cédula

→ detectar duplicados

→ importar registros válidos

→ informar errores

→ guardar historial de importación



Cada importación debe registrar:



archivo

usuario

fecha

filas encontradas

filas importadas

filas rechazadas

duplicados

errores



No insertar datos silenciosamente si existen errores.



Mostrar un resumen como:



1250 registros encontrados

1218 importados

20 duplicados

12 con errores



Permitir descargar o visualizar el detalle de errores.



Diseña el importador para que posteriormente pueda reutilizarse en otros módulos.



==================================================

8\. ACCIDENTES

==================================================



Crear módulo de Accidentes dentro de Departamento Médico.



Debe permitir:



\- Registro manual.

\- Importación desde Excel.

\- Vinculación con Persona.

\- Seguimientos.

\- Formularios.

\- Documentos.

\- Estado.

\- Clasificación.

\- Notificaciones.

\- Historial.



El importador debe reutilizar el motor creado para Ausentismo cuando sea posible.



==================================================

9\. NOTIFICACIONES

==================================================



Crear una arquitectura de notificaciones.



Inicialmente debe permitir:



EMAIL

WHATSAPP



Para correo crea un servicio desacoplado del frontend.



Para WhatsApp NO utilices automatizaciones no oficiales ni WhatsApp Web.



La integración debe quedar preparada para utilizar WhatsApp Business Cloud API o un proveedor autorizado.



Si actualmente no existen credenciales:



\- crea la arquitectura,

\- variables de entorno,

\- interfaces,

\- configuración,

\- servicios,

\- estados de envío,

\- logs,



pero NO inventes tokens ni credenciales.



Las notificaciones deben poder vincularse con reglas como:



Nuevo accidente

→ enviar correo



Accidente grave

→ correo + WhatsApp



Seguimiento vencido

→ generar alerta



Registrar:



canal

destinatario

fecha

estado

respuesta

error

intentos

entidad relacionada



==================================================

10\. ENCUESTAS

==================================================



Crear un módulo central de ENCUESTAS.



No quiero tres motores independientes.



Crear un solo motor y permitir categorizar las encuestas en:



Producción

Operaciones

Oficina



Una encuesta debe contener:



Nombre

Descripción

Área

Población objetivo

Fecha inicio

Fecha fin

Estado

Preguntas

Anónima Sí/No

Editable Sí/No

Creador

Fecha de creación



Estados:



Borrador

Publicada

Cerrada

Archivada



Debe permitir:



crear

editar

duplicar

publicar

cerrar

consultar respuestas

visualizar resultados



Reutiliza el motor de formularios si arquitectónicamente tiene sentido.



==================================================

11\. BENEFICIOS

==================================================



Crear módulo:



Beneficios



Inicialmente:



Seguros

Tía

Otros beneficios

Formularios de atención



Diseña la arquitectura para poder agregar nuevos beneficios sin tener que modificar masivamente el código.



==================================================

12\. SEGUROS

==================================================



Este módulo requiere especial atención.



Debe administrar:



Titulares

Dependientes

Planes

Coberturas

Tarifas

Fechas de ingreso

Fechas de salida

Fecha de corte

Descuentos

Acumulados

Mes de nómina

Historial



Inicialmente existirán planes asociados a coberturas como:



5K

20K



NO hardcodees los valores económicos en el código.



Crear configuración administrativa de:



Plan

Cobertura

Valor titular

Valor dependiente

Vigencia desde

Vigencia hasta

Estado



==================================================

13\. DEPENDIENTES

==================================================



Una persona podrá registrar uno o varios dependientes.



Datos mínimos:



Nombre

Cédula/identificación

Parentesco

Fecha de nacimiento

Plan

Fecha de ingreso

Fecha de salida

Estado

Valor aplicable



Relacionar dependientes con el colaborador titular.



==================================================

14\. MOTOR DE CÁLCULO DE DESCUENTOS

==================================================



Crear un motor de cálculo separado de la interfaz.



No quiero que las fórmulas estén distribuidas en componentes React.



El backend debe ser la fuente oficial del cálculo.



Debe soportar:



\- titular

\- dependientes

\- plan 5K

\- plan 20K

\- tarifas configurables

\- fecha efectiva

\- fecha de corte

\- acumulación

\- mes de nómina

\- ajustes



Quiero poder configurar la fecha de corte.



Ejemplo:



Fecha de corte mensual: día 15



Caso A:



Ingreso: 10 de septiembre

Corte: 15 de septiembre



Debe poder cobrarse en septiembre según las reglas configuradas.



Caso B:



Ingreso: 20 de septiembre

Corte: 15 de septiembre



El valor correspondiente debe poder quedar pendiente y acumularse para la nómina de octubre.



Ejemplo conceptual:



Septiembre pendiente: $12

Octubre normal: $12

Total descuento octubre: $24



NO asumas valores como $12.

Los valores deben provenir de las tarifas configuradas.



Guardar siempre:



periodo generado

valor base

valor dependientes

valor acumulado

ajustes

valor total

periodo de cobro

fecha de corte aplicada

estado



Estados sugeridos:



Pendiente

Calculado

Enviado a nómina

Cobrado

Ajustado

Anulado



==================================================

15\. CONFIGURACIÓN DE SEGUROS

==================================================



Crear pantalla administrativa donde un usuario autorizado pueda cambiar:



Día de corte

Planes

Coberturas

Tarifas

Tarifa titular

Tarifa dependiente

Acumulación posterior al corte

Reglas vigentes



Los cambios deben tener fecha de vigencia.



No modificar cálculos históricos cuando cambie una tarifa nueva.



==================================================

16\. HISTORIAL Y TRAZABILIDAD

==================================================



Todo proceso crítico debe registrar auditoría.



Especialmente:



Seguros

Dependientes

Tarifas

Accidentes

Riesgos de trabajo

Formularios

Importaciones

Notificaciones



Quiero saber:



quién

qué hizo

cuándo

qué registro

valor anterior

valor nuevo



==================================================

17\. ARCHIVOS Y DOCUMENTOS

==================================================



Crea una estrategia reutilizable para documentos.



Los documentos podrán estar asociados con:



Persona

Caso

Riesgo

Accidente

Seguro

Formulario

otro proceso



Guardar metadatos como:



nombre

tipo

tamaño

usuario

fecha

entidad relacionada



No dupliques la lógica de archivos por cada módulo.



==================================================

18\. ROLES Y PERMISOS

==================================================



La información médica, social y de beneficios no debe estar disponible para todos.



Amplía el sistema de permisos existente.



Debe poder controlar permisos por:



módulo

acción



Ejemplos:



ver

crear

editar

eliminar

importar

exportar

configurar

auditar



Ejemplo:



Trabajo Social puede visualizar ciertos procesos.



Departamento Médico puede visualizar Riesgos, Accidentes y Ausentismo.



Administrador puede configurar catálogos.



No confíes solamente en ocultar botones en React.

Las autorizaciones también deben comprobarse en backend.



==================================================

19\. BASE DE DATOS

==================================================



Analiza primero el modelo actual.



Actualmente no quiero que destruyas ni reinicies la base existente.



Crea migraciones compatibles con los datos existentes.



Diseña las nuevas tablas correctamente normalizadas.



Evita guardar estructuras importantes como JSON cuando deberían ser entidades relacionales.



Puedes utilizar JSON para respuestas dinámicas de formularios cuando tenga sentido.



La arquitectura debe quedar preparada para una futura migración a PostgreSQL aunque actualmente el proyecto esté utilizando SQLite.



No realices una migración destructiva a PostgreSQL en esta tarea salvo que sea estrictamente necesaria.



==================================================

20\. API

==================================================



Mantén una API organizada.



Usa rutas consistentes, por ejemplo:



/api/v1/personas

/api/v1/medical/riesgos

/api/v1/medical/ausentismo

/api/v1/medical/accidentes

/api/v1/encuestas

/api/v1/beneficios

/api/v1/seguros

/api/v1/importaciones

/api/v1/notificaciones

/api/v1/auditoria



Adapta estos nombres a las convenciones actuales del proyecto si ya existe una estructura mejor.



No rompas endpoints existentes.



==================================================

21\. FRONTEND

==================================================



Mantén la identidad visual actual del aplicativo.



Reutiliza:



cards

modales

inputs

tablas

toasts

confirmaciones

sidebar

formularios

componentes de carga

estados vacíos



Quiero que las nuevas pantallas parezcan parte del mismo sistema y no módulos construidos por desarrolladores diferentes.



Las pantallas deben ser responsive.



==================================================

22\. DASHBOARDS

==================================================



Deja preparados dashboards por módulo.



Departamento Médico:

\- Riesgos abiertos

\- Accidentes

\- Ausentismo

\- Casos pendientes

\- Seguimientos vencidos



Encuestas:

\- Encuestas activas

\- Participación

\- Respuestas



Seguros:

\- Afiliados

\- Dependientes

\- Valores del mes

\- Pendientes

\- Acumulados

\- Movimientos posteriores al corte



No inventes KPIs que no puedan calcularse con información disponible.



==================================================

23\. RENDIMIENTO

==================================================



Evita consultas N+1.



Implementa paginación para tablas grandes.



No cargues miles de registros en el navegador innecesariamente.



Los importadores de Excel deben poder manejar volúmenes grandes de manera segura.



Las vistas deben mostrar estados de carga y errores correctamente.



==================================================

24\. SEGURIDAD

==================================================



Valida archivos cargados.



Valida tamaño, extensión y estructura.



Sanitiza datos cuando corresponda.



No expongas secretos en frontend.



Usa variables de entorno para servicios externos.



Mantén autenticación y autorización en backend.



==================================================

25\. PRUEBAS

==================================================



Agrega pruebas para las funcionalidades críticas.



Especialmente:



\- cálculo de fecha de corte

\- acumulación al siguiente mes

\- dependientes

\- tarifas

\- importación de Excel

\- detección de duplicados

\- permisos

\- formularios

\- auditoría



Crear casos de prueba como:



Ingreso antes del corte.

Ingreso exactamente el día del corte.

Ingreso después del corte.

Cambio de plan.

Ingreso de dependiente.

Salida de dependiente.

Cambio de tarifa.

Acumulación de meses.

Anulación.

Ajuste manual.



==================================================

26\. FORMA DE TRABAJO

==================================================



NO intentes implementar todo de manera desordenada.



Primero:



1\. Inspecciona completamente el proyecto.

2\. Identifica arquitectura existente.

3\. Identifica modelos reutilizables.

4\. Identifica componentes reutilizables.

5\. Revisa sistema de formularios.

6\. Revisa autenticación/permisos.

7\. Revisa migraciones actuales.

8\. Diseña el modelo de datos.

9\. Define el plan de implementación.

10\. Después comienza a modificar.



Trabaja por fases internamente:



FASE 1

Arquitectura, menú jerárquico, permisos y modelos base.



FASE 2

Departamento Médico:

Riesgos + Ausentismo + Accidentes.



FASE 3

Importador reutilizable de Excel.



FASE 4

Encuestas.



FASE 5

Beneficios y Seguros.



FASE 6

Motor de cálculo y fecha de corte.



FASE 7

Notificaciones Email/WhatsApp.



FASE 8

Auditoría, dashboards, optimización y pruebas.



No dejes código muerto, mocks innecesarios ni botones que aparenten funcionar cuando todavía no existe backend.



Si una integración externa requiere credenciales, construye correctamente el soporte técnico y deja claramente documentado qué variable debe configurarse.



==================================================

27\. CRITERIOS DE ACEPTACIÓN

==================================================



Al finalizar quiero poder:



\- Entrar al sistema normalmente.

\- Mantener funcionando los módulos existentes.

\- Navegar mediante la nueva estructura jerárquica.

\- Crear y consultar personas.

\- Abrir la ficha integral de una persona.

\- Crear Riesgos de Trabajo.

\- Agregar seguimientos.

\- Asociar formularios.

\- Importar Ausentismo desde Excel.

\- Importar Accidentes desde Excel.

\- Consultar errores de importación.

\- Crear encuestas para Producción, Operaciones y Oficina.

\- Registrar seguros.

\- Registrar dependientes.

\- Configurar planes 5K y 20K.

\- Configurar tarifas sin modificar código.

\- Configurar fecha de corte.

\- Calcular descuentos.

\- Acumular automáticamente valores posteriores al corte.

\- Consultar por qué se calculó determinado descuento.

\- Editar registros autorizados dejando historial.

\- Consultar auditoría.

\- Dejar preparada la integración de Email.

\- Dejar preparada la integración oficial de WhatsApp.

\- Mantener permisos por módulo.

\- Utilizar la aplicación correctamente desde desktop y móvil.



==================================================

28\. ENTREGA TÉCNICA

==================================================



Cuando termines:



\- Ejecuta las migraciones necesarias.

\- Ejecuta tests del backend.

\- Ejecuta tests del frontend.

\- Ejecuta lint si existe.

\- Ejecuta build de producción del frontend.

\- Corrige errores encontrados.

\- No declares terminado mientras el build esté roto.



Entrégame un resumen final indicando:



ARCHIVOS PRINCIPALES MODIFICADOS



NUEVAS TABLAS/MODELOS



NUEVOS ENDPOINTS



NUEVAS PANTALLAS



MIGRACIONES REALIZADAS



PRUEBAS CREADAS



VARIABLES DE ENTORNO NUEVAS



FUNCIONALIDADES COMPLETADAS



FUNCIONALIDADES QUE REQUIEREN CREDENCIALES EXTERNAS



RIESGOS O PENDIENTES



COMANDOS EXACTOS PARA PROBARLO LOCALMENTE



Si utilizas Git:

\- No sobrescribas trabajo existente.

\- Revisa git status antes de comenzar.

\- No borres cambios locales ajenos.

\- Haz commits lógicos y descriptivos si el entorno permite hacerlo.



Empieza ahora inspeccionando el repositorio y posteriormente implementa el trabajo.
