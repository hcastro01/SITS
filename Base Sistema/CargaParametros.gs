/**
 * Carga inicial idempotente del formulario de gestion de casos.
 *
 * Ejecutar manualmente desde el editor de Apps Script con una cuenta
 * administradora. La funcion crea solo las preguntas que falten, no modifica
 * preguntas existentes y deja el formulario en BORRADOR para su revision.
 *
 * Las opciones institucionales que no fueron suministradas se mantienen como
 * texto corto. De este modo no se inventan categorias y el formulario sigue
 * siendo utilizable. Cuando existan los valores oficiales, pueden convertirse
 * a listas desde el constructor de formularios o mediante otra carga masiva.
 */
function cargarParametrosFormularioCaso() {
  var correlationId = 'CARGA-PARAMETROS-CASO-' + Utilities.getUuid();
  var user = TSAuth.authorize('FORMULARIOS', 'create');
  var formName = 'Ficha integral de gestion de casos';
  var form = TSData.list('Formularios', {
    includeDeleted: true,
    cache: false,
    predicate: function (row) {
      return TSUtils.normalizeKey(row.Nombre) === TSUtils.normalizeKey(formName) &&
        TSUtils.normalizeKey(row.Proceso) === 'CASO';
    },
    limit: 1
  }).rows[0];

  if (form) {
    TSErrors.assert(
      TSData.isVisible(form, false),
      'FORM_TEMPLATE_INACTIVE',
      'Ya existe una ficha integral inactiva. Reactivela antes de volver a ejecutar la carga.',
      { formId: form.IdFormulario },
      409
    );
  } else {
    form = TSForms.saveDefinition({
      form: {
        Nombre: formName,
        Descripcion: 'Registro integral de casos, colaborador, evento, derivacion y restricciones.',
        Proceso: 'CASO',
        Estado: 'BORRADOR',
        Responsable: user.email
      }
    }, correlationId);
  }

  var definitions = parametrosFormularioCaso_();
  var existing = TSData.list('Preguntas', {
    includeDeleted: true,
    cache: false,
    filters: { IdFormulario: form.IdFormulario }
  }).rows;
  var byLabel = {};
  existing.forEach(function (question) {
    byLabel[TSUtils.normalizeKey(question.Etiqueta)] = question;
  });

  var missing = definitions.filter(function (definition) {
    return !byLabel[TSUtils.normalizeKey(definition.Etiqueta)];
  });
  if (missing.length && TSUtils.normalizeKey(form.Estado) === 'PUBLICADO') {
    throw new TSAppError(
      'FORM_TEMPLATE_PUBLISHED',
      'El formulario ya esta publicado. Cambielo a BORRADOR antes de agregar preguntas faltantes.',
      { formId: form.IdFormulario, missingQuestions: missing.length },
      409
    );
  }

  var created = [];
  var skipped = [];
  var idsByLabel = {};
  existing.forEach(function (question) {
    idsByLabel[TSUtils.normalizeKey(question.Etiqueta)] = question.IdPregunta;
  });

  definitions.forEach(function (definition, index) {
    var labelKey = TSUtils.normalizeKey(definition.Etiqueta);
    if (byLabel[labelKey]) {
      skipped.push(definition.Etiqueta);
      return;
    }

    var payload = {};
    Object.keys(definition).forEach(function (key) {
      if (key !== 'DependeDe') payload[key] = definition[key];
    });
    payload.IdFormulario = form.IdFormulario;
    payload.Orden = index + 1;

    if (definition.DependeDe) {
      var dependencyId = idsByLabel[TSUtils.normalizeKey(definition.DependeDe)];
      TSErrors.assert(
        dependencyId,
        'FORM_DEPENDENCY_MISSING',
        'No se encontro la pregunta de la cual depende ' + definition.Etiqueta + '.',
        { dependency: definition.DependeDe },
        409
      );
      payload.CampoDependiente = dependencyId;
      payload.ValorDependiente = 'true';
      payload.CondicionVisibilidad = JSON.stringify({ operator: 'EQ', value: 'true' });
    }

    var savedDefinition = TSForms.saveQuestion(payload, correlationId);
    var savedQuestion = savedDefinition.questions.filter(function (question) {
      return TSUtils.normalizeKey(question.Etiqueta) === labelKey;
    })[0];
    TSErrors.assert(
      savedQuestion,
      'QUESTION_SEED_FAILED',
      'No se pudo confirmar la creacion de la pregunta ' + definition.Etiqueta + '.',
      null,
      500
    );
    byLabel[labelKey] = savedQuestion;
    idsByLabel[labelKey] = savedQuestion.IdPregunta;
    created.push(definition.Etiqueta);
  });

  var automaticCode = asegurarCodigoCasoAutomatico_(form.IdFormulario, correlationId);

  return {
    formId: form.IdFormulario,
    formName: form.Nombre,
    status: form.Estado,
    totalConfiguredFields: definitions.length,
    createdQuestions: created.length,
    skippedQuestions: skipped.length,
    createdLabels: created,
    automaticCaseCode: automaticCode,
    pendingInstitutionalCatalogs: [
      'TIPO_CASO', 'PRIORIDAD', 'TIPO_GESTION', 'TECNICA_INSTRUMENTO',
      'SEXO', 'DEPARTAMENTO', 'SUB_CENTRO', 'TURNO',
      'ESTADO_DERIVACION', 'TIPO_EVENTO', 'CONDICION_LABORAL', 'AREA'
    ],
    message: created.length ?
      'Carga completada. Revise la vista previa y los catalogos antes de publicar.' :
      'El formulario ya contenia los 22 campos; no se crearon duplicados.'
  };
}

/**
 * Oculta cualquier pregunta CodigoCaso de los formularios de proceso CASO.
 * El valor se genera exclusivamente en TSCases.save(), en el servidor, para
 * impedir codigos repetidos o manipulados por el usuario.
 */
function configurarCodigoCasoAutomatico() {
  TSAuth.authorize('FORMULARIOS', 'edit');
  var correlationId = 'CONFIG-CODIGO-CASO-' + Utilities.getUuid();
  var forms = TSData.list('Formularios', {
    cache: false,
    predicate: function (row) {
      return TSUtils.normalizeKey(row.Proceso) === 'CASO';
    }
  }).rows;
  var results = forms.map(function (form) {
    var result = asegurarCodigoCasoAutomatico_(form.IdFormulario, correlationId);
    result.formId = form.IdFormulario;
    result.formName = form.Nombre;
    return result;
  });
  return {
    formsReviewed: forms.length,
    questionsUpdated: results.reduce(function (total, item) { return total + item.updatedQuestions; }, 0),
    alreadyConfigured: results.reduce(function (total, item) { return total + item.alreadyConfigured; }, 0),
    format: 'CAS-AAAA-XXXXXXXXXX',
    results: results,
    message: 'CodigoCaso se genera automaticamente al crear cada caso y no puede ser editado por el usuario.'
  };
}

function asegurarCodigoCasoAutomatico_(formId, correlationId) {
  var questions = TSData.list('Preguntas', {
    cache: false,
    filters: { IdFormulario: formId },
    predicate: function (row) {
      var key = TSUtils.normalizeKey(row.Etiqueta);
      return key === 'CODIGOCASO' || key === 'CODIGO_CASO' || key === 'CODIGO_DEL_CASO';
    }
  }).rows;
  var updated = 0;
  var configured = 0;

  questions.forEach(function (question) {
    var isAutomatic = TSUtils.normalizeKey(question.Tipo) === 'CAMPO_OCULTO' &&
      !TSUtils.toBoolean(question.Obligatoria) &&
      TSUtils.toBoolean(question.SoloLectura) &&
      TSUtils.isBlank(question.ValorPredeterminado);
    if (isAutomatic) {
      configured += 1;
      return;
    }
    TSForms.saveQuestion({
      IdPregunta: question.IdPregunta,
      IdFormulario: question.IdFormulario,
      Etiqueta: question.Etiqueta,
      Descripcion: 'Codigo unico generado automaticamente por el servidor al crear el caso.',
      Tipo: 'CAMPO_OCULTO',
      Obligatoria: false,
      Orden: question.Orden,
      Categoria: question.Categoria || 'DATOS_CASO',
      Subcategoria: question.Subcategoria || '',
      ValorPredeterminado: '',
      TextoAyuda: '',
      Visible: true,
      SoloLectura: true,
      LongitudMaxima: '',
      Validacion: '',
      Sensibilidad: question.Sensibilidad || '',
      CondicionVisibilidad: '',
      CampoDependiente: '',
      ValorDependiente: '',
      Formula: '',
      expectedVersion: question.Version,
      options: []
    }, correlationId);
    updated += 1;
  });

  return {
    codeQuestionsFound: questions.length,
    updatedQuestions: updated,
    alreadyConfigured: configured,
    serverGeneratesCodeEvenWithoutQuestion: true
  };
}

function parametrosFormularioCaso_() {
  return [
    {
      Etiqueta: 'CodigoCaso',
      Descripcion: 'Codigo unico generado automaticamente por el servidor al crear el caso.',
      Tipo: 'CAMPO_OCULTO',
      Obligatoria: false,
      Categoria: 'DATOS_CASO',
      ValorPredeterminado: '',
      TextoAyuda: '',
      Visible: true,
      SoloLectura: true
    },
    {
      Etiqueta: 'Responsable',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: true,
      Categoria: 'DATOS_CASO',
      TextoAyuda: 'Ingrese el correo o nombre del responsable.',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 200
    },
    {
      Etiqueta: 'Fecha y Hora',
      Descripcion: 'Se guarda como fecha de apertura del caso.',
      Tipo: 'FECHA_HORA',
      Obligatoria: true,
      Categoria: 'DATOS_CASO',
      Visible: true,
      SoloLectura: false
    },
    {
      Etiqueta: 'Tipo de Caso',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: false,
      Categoria: 'DATOS_CASO',
      TextoAyuda: 'Pendiente de cargar los valores oficiales del catalogo TIPO_CASO.',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 200
    },
    {
      Etiqueta: 'Prioridad',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: false,
      Categoria: 'DATOS_CASO',
      TextoAyuda: 'Pendiente de cargar los valores oficiales del catalogo PRIORIDAD.',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 120
    },
    {
      Etiqueta: 'Tipo de gestión',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: false,
      Categoria: 'DATOS_CASO',
      TextoAyuda: 'Pendiente de cargar los valores oficiales del catalogo TIPO_GESTION.',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 200
    },
    {
      Etiqueta: 'EstadoCaso',
      Tipo: 'LISTA_DESPLEGABLE',
      Obligatoria: true,
      Categoria: 'DATOS_CASO',
      ValorPredeterminado: 'BORRADOR',
      Visible: true,
      SoloLectura: false,
      options: [
        { Valor: 'BORRADOR', Etiqueta: 'Borrador', Orden: 1 },
        { Valor: 'REGISTRADO', Etiqueta: 'Registrado', Orden: 2 },
        { Valor: 'EN_GESTION', Etiqueta: 'En gestion', Orden: 3 },
        { Valor: 'CERRADO', Etiqueta: 'Cerrado', Orden: 4 }
      ]
    },
    {
      Etiqueta: 'Técnica/Instrumento de Bienestar Social',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: false,
      Categoria: 'DATOS_CASO',
      TextoAyuda: 'Pendiente de cargar los valores oficiales del catalogo TECNICA_INSTRUMENTO.',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 250
    },
    {
      Etiqueta: 'Coloqué el número de cédula del colaborador',
      Descripcion: 'El selector consulta la tabla Personas y vincula el caso con el colaborador.',
      Tipo: 'PERSONA',
      Obligatoria: true,
      Categoria: 'DATOS_COLABORADOR',
      TextoAyuda: 'Busque por cédula, nombre o código de empleado.',
      Visible: true,
      SoloLectura: false,
      Sensibilidad: 'SI'
    },
    {
      Etiqueta: 'Sexo',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: false,
      Categoria: 'DATOS_COLABORADOR',
      TextoAyuda: 'Pendiente de validar el catalogo institucional y su politica de datos personales.',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 120,
      Sensibilidad: 'SI'
    },
    {
      Etiqueta: 'Cargo',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: false,
      Categoria: 'DATOS_COLABORADOR',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 250
    },
    {
      Etiqueta: 'Departamento',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: false,
      Categoria: 'DATOS_COLABORADOR',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 250
    },
    {
      Etiqueta: 'Sub-centro',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: false,
      Categoria: 'DATOS_COLABORADOR',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 250
    },
    {
      Etiqueta: 'En qué turno ocurrió el evento',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: false,
      Categoria: 'DATOS_COLABORADOR',
      TextoAyuda: 'Pendiente de cargar los turnos oficiales.',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 120
    },
    {
      Etiqueta: 'Derivación',
      Tipo: 'SI_NO',
      Obligatoria: false,
      Categoria: 'DERIVACION_EVENTO',
      ValorPredeterminado: 'false',
      Visible: true,
      SoloLectura: false
    },
    {
      Etiqueta: 'Estado de la derivación',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: false,
      Categoria: 'DERIVACION_EVENTO',
      TextoAyuda: 'Se muestra cuando Derivación es Sí. Pendiente del catálogo ESTADO_DERIVACION.',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 160,
      DependeDe: 'Derivación'
    },
    {
      Etiqueta: 'Tipo de Evento',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: false,
      Categoria: 'DERIVACION_EVENTO',
      TextoAyuda: 'Pendiente de cargar los valores oficiales del catalogo TIPO_EVENTO.',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 200
    },
    {
      Etiqueta: 'Condición laboral',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: false,
      Categoria: 'RESTRICCION_RIESGO',
      TextoAyuda: 'Pendiente de cargar los valores oficiales del catalogo CONDICION_LABORAL.',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 200
    },
    {
      Etiqueta: 'Fecha de Inicio de Restricción',
      Tipo: 'FECHA',
      Obligatoria: false,
      Categoria: 'RESTRICCION_RIESGO',
      Visible: true,
      SoloLectura: false
    },
    {
      Etiqueta: 'Fecha de culminación de Restricción',
      Tipo: 'FECHA',
      Obligatoria: false,
      Categoria: 'RESTRICCION_RIESGO',
      Visible: true,
      SoloLectura: false
    },
    {
      Etiqueta: 'Se reportó a Riesgo de Trabajo',
      Tipo: 'SI_NO',
      Obligatoria: false,
      Categoria: 'RESTRICCION_RIESGO',
      ValorPredeterminado: 'false',
      Visible: true,
      SoloLectura: false
    },
    {
      Etiqueta: 'A qué área se lo designa',
      Tipo: 'TEXTO_CORTO',
      Obligatoria: false,
      Categoria: 'RESTRICCION_RIESGO',
      TextoAyuda: 'Pendiente de cargar las areas oficiales.',
      Visible: true,
      SoloLectura: false,
      LongitudMaxima: 250
    }
  ];
}
