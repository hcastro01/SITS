import type { FormQuestion, FormRule, FormSection, SearchSource } from '../../api/formBuilder';

export const QUESTION_TYPES = [
  ['TEXTO_CORTO', 'Texto corto'], ['TEXTO_LARGO', 'Texto largo / párrafo'],
  ['NUMERO_ENTERO', 'Número entero'], ['NUMERO_DECIMAL', 'Número decimal'], ['MONEDA', 'Moneda'],
  ['PORCENTAJE', 'Porcentaje'], ['EMAIL', 'Correo electrónico'], ['TELEFONO', 'Teléfono'],
  ['DOCUMENTO', 'Cédula / documento'], ['FECHA', 'Fecha'], ['HORA', 'Hora'], ['FECHA_HORA', 'Fecha y hora'],
  ['SI_NO', 'Sí / No'], ['SELECCION_UNICA', 'Selección única'], ['LISTA_DESPLEGABLE', 'Lista desplegable'],
  ['SELECCION_MULTIPLE', 'Selección múltiple'], ['CASILLAS', 'Casillas de verificación'],
  ['ESCALA', 'Escala lineal'], ['CALIFICACION', 'Calificación'], ['BUSQUEDA', 'Búsqueda / autocompletado'],
  ['ARCHIVO', 'Archivo'], ['FOTOGRAFIA', 'Imagen / fotografía'], ['TITULO', 'Título de sección'],
  ['INFORMATIVO', 'Texto informativo'],
] as const;

const OPTION_TYPES = new Set(['SELECCION_UNICA', 'LISTA_DESPLEGABLE', 'SELECCION_MULTIPLE', 'CASILLAS']);
const OPERATORS = [
  ['EQ', 'Es igual a'], ['NE', 'Es diferente de'], ['CONTAINS', 'Contiene'], ['NOT_CONTAINS', 'No contiene'],
  ['GT', 'Mayor que'], ['GTE', 'Mayor o igual'], ['LT', 'Menor que'], ['LTE', 'Menor o igual'],
  ['EMPTY', 'Está vacío'], ['NOT_EMPTY', 'No está vacío'], ['INCLUDES', 'Incluye opción'], ['NOT_INCLUDES', 'No incluye opción'],
] as const;

function uid() { return crypto.randomUUID(); }

export function QuestionEditor({ question, index, total, sections, allQuestions, rules, sources,
  onChange, onRulesChange, onDuplicate, onDelete, onMove }: {
  question: FormQuestion; index: number; total: number; sections: FormSection[];
  allQuestions: FormQuestion[]; rules: FormRule[]; sources: SearchSource[];
  onChange: (question: FormQuestion) => void; onRulesChange: (rules: FormRule[]) => void;
  onDuplicate: () => void; onDelete: () => void; onMove: (direction: -1 | 1) => void;
}) {
  const ownRules = rules.filter((rule) => rule.id_pregunta_destino === question.id_pregunta);
  const selectedSource = sources.find((source) => source.codigo === (question.fuente_datos ?? 'PERSONAS'));
  const updateConfig = (key: string, value: unknown) => onChange({ ...question, configuracion: { ...question.configuracion, [key]: value } });
  const updateValidation = (key: string, value: unknown) => onChange({ ...question, validacion: { ...question.validacion, [key]: value } });
  const setRule = (id: string, patch: Partial<FormRule>) => onRulesChange(rules.map((rule) => rule.id_regla === id ? { ...rule, ...patch } : rule));

  return <article className="question-editor">
    <div className="question-editor-header">
      <div><span className="question-number">Pregunta {index + 1}</span><strong>{question.etiqueta || 'Sin título'}</strong></div>
      <div className="question-order-actions">
        <button type="button" className="ghost icon-button" aria-label="Mover arriba" disabled={index === 0} onClick={() => onMove(-1)}>↑</button>
        <button type="button" className="ghost icon-button" aria-label="Mover abajo" disabled={index === total - 1} onClick={() => onMove(1)}>↓</button>
      </div>
    </div>
    <div className="builder-grid">
      <label className="builder-field builder-field--wide">Título
        <input value={question.etiqueta} onChange={(e) => onChange({ ...question, etiqueta: e.target.value })} />
      </label>
      <label className="builder-field">Tipo
        <select value={question.tipo} onChange={(e) => onChange({ ...question, tipo: e.target.value,
          opciones: OPTION_TYPES.has(e.target.value) && question.opciones.length === 0 ? [
            { id_opcion: uid(), valor: 'Opción 1', etiqueta: 'Opción 1', orden: 0 },
            { id_opcion: uid(), valor: 'Opción 2', etiqueta: 'Opción 2', orden: 1 },
          ] : question.opciones })}>
          {QUESTION_TYPES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </label>
      <label className="builder-field">Sección
        <select value={question.id_seccion ?? ''} onChange={(e) => onChange({ ...question, id_seccion: e.target.value || null })}>
          <option value="">Sin sección</option>{sections.map((s) => <option key={s.id_seccion} value={s.id_seccion}>{s.titulo}</option>)}
        </select>
      </label>
      <label className="builder-field builder-field--wide">Descripción / ayuda
        <input value={question.descripcion ?? ''} onChange={(e) => onChange({ ...question, descripcion: e.target.value || null })} />
      </label>
      {!['TITULO', 'INFORMATIVO'].includes(question.tipo) && <>
        <label className="toggle-field"><input type="checkbox" checked={question.obligatoria} onChange={(e) => onChange({ ...question, obligatoria: e.target.checked })} /> Obligatoria</label>
        <label className="toggle-field"><input type="checkbox" checked={question.solo_lectura} onChange={(e) => onChange({ ...question, solo_lectura: e.target.checked })} /> Solo lectura</label>
      </>}
      {['TEXTO_CORTO', 'TEXTO_LARGO', 'EMAIL', 'TELEFONO', 'DOCUMENTO', 'BUSQUEDA'].includes(question.tipo) && <>
        <label className="builder-field">Placeholder<input value={String(question.configuracion.placeholder ?? '')} onChange={(e) => updateConfig('placeholder', e.target.value)} /></label>
        <label className="builder-field">Longitud mínima<input type="number" min="0" value={String(question.validacion.min_length ?? '')} onChange={(e) => updateValidation('min_length', e.target.value ? Number(e.target.value) : null)} /></label>
        <label className="builder-field">Longitud máxima<input type="number" min="1" value={String(question.validacion.max_length ?? '')} onChange={(e) => updateValidation('max_length', e.target.value ? Number(e.target.value) : null)} /></label>
      </>}
      {['NUMERO_ENTERO', 'NUMERO_DECIMAL', 'MONEDA', 'PORCENTAJE'].includes(question.tipo) && <>
        <label className="builder-field">Mínimo<input type="number" value={String(question.validacion.min ?? '')} onChange={(e) => updateValidation('min', e.target.value ? Number(e.target.value) : null)} /></label>
        <label className="builder-field">Máximo<input type="number" value={String(question.validacion.max ?? '')} onChange={(e) => updateValidation('max', e.target.value ? Number(e.target.value) : null)} /></label>
      </>}
      {['ESCALA', 'CALIFICACION'].includes(question.tipo) && <>
        <label className="builder-field">Valor mínimo<input type="number" min="0" max="10" value={String(question.configuracion.min ?? 1)} onChange={(e) => updateConfig('min', Number(e.target.value))} /></label>
        <label className="builder-field">Valor máximo<input type="number" min="2" max="10" value={String(question.configuracion.max ?? 5)} onChange={(e) => updateConfig('max', Number(e.target.value))} /></label>
      </>}
      {question.tipo === 'BUSQUEDA' && <>
        <label className="builder-field">Fuente segura
          <select value={question.fuente_datos ?? 'PERSONAS'} onChange={(e) => onChange({ ...question, fuente_datos: e.target.value, mapping: {} })}>
            {sources.map((source) => <option key={source.codigo} value={source.codigo}>{source.label}</option>)}
          </select>
        </label>
        <div className="builder-field builder-field--wide mapping-editor"><strong>Autocompletar otros campos</strong>
          <p>Asigne únicamente los datos que desea copiar al seleccionar un resultado.</p>
          <div className="mapping-grid">{selectedSource?.mapping_fields.map((field) => <label key={field}>{field}
            <select value={question.mapping[field] ?? ''} onChange={(e) => onChange({ ...question, mapping: { ...question.mapping, [field]: e.target.value } })}>
              <option value="">No copiar</option>
              {allQuestions.filter((item) => item.id_pregunta !== question.id_pregunta).map((item) => <option key={item.id_pregunta} value={item.id_pregunta}>{item.etiqueta}</option>)}
            </select>
          </label>)}</div>
        </div>
      </>}
      {['ARCHIVO', 'FOTOGRAFIA'].includes(question.tipo) && <label className="builder-field">Cantidad máxima
        <input type="number" min="1" max="10" value={String(question.configuracion.max_files ?? 1)} onChange={(e) => updateConfig('max_files', Number(e.target.value))} />
      </label>}
    </div>

    {OPTION_TYPES.has(question.tipo) && <div className="option-editor"><h4>Opciones</h4>
      {question.opciones.map((option, optionIndex) => <div className="option-row" key={option.id_opcion}>
        <span>{optionIndex + 1}.</span><input aria-label={`Opción ${optionIndex + 1}`} value={option.etiqueta}
          onChange={(e) => onChange({ ...question, opciones: question.opciones.map((item) => item.id_opcion === option.id_opcion ? { ...item, etiqueta: e.target.value, valor: e.target.value } : item) })} />
        <div className="option-order-actions">
          <button type="button" className="ghost icon-button" aria-label={`Mover opción ${optionIndex + 1} arriba`} disabled={optionIndex === 0} onClick={() => { const next = [...question.opciones]; [next[optionIndex - 1], next[optionIndex]] = [next[optionIndex], next[optionIndex - 1]]; onChange({ ...question, opciones: next.map((item, orden) => ({ ...item, orden })) }); }}>↑</button>
          <button type="button" className="ghost icon-button" aria-label={`Mover opción ${optionIndex + 1} abajo`} disabled={optionIndex === question.opciones.length - 1} onClick={() => { const next = [...question.opciones]; [next[optionIndex], next[optionIndex + 1]] = [next[optionIndex + 1], next[optionIndex]]; onChange({ ...question, opciones: next.map((item, orden) => ({ ...item, orden })) }); }}>↓</button>
        </div>
        <button type="button" className="ghost" onClick={() => onChange({ ...question, opciones: question.opciones.filter((item) => item.id_opcion !== option.id_opcion) })}>Eliminar</button>
      </div>)}
      <button type="button" className="secondary" onClick={() => onChange({ ...question, opciones: [...question.opciones,
        { id_opcion: uid(), etiqueta: `Opción ${question.opciones.length + 1}`, valor: `Opción ${question.opciones.length + 1}`, orden: question.opciones.length }] })}>+ Agregar opción</button>
    </div>}

    <div className="condition-editor"><div className="section-heading"><h4>Condiciones</h4>
      <button type="button" className="secondary" disabled={allQuestions.length < 2} onClick={() => onRulesChange([...rules, {
        id_regla: uid(), id_pregunta_origen: allQuestions.find((item) => item.id_pregunta !== question.id_pregunta)?.id_pregunta ?? '',
        operador: 'EQ', valor_comparacion: '', id_pregunta_destino: question.id_pregunta, id_seccion_destino: null,
        accion: 'MOSTRAR', grupo: 'TODAS', orden: rules.length,
      }])}>+ Agregar condición</button></div>
      {ownRules.map((rule) => <div className="condition-row" key={rule.id_regla}>
        <label>Pregunta<select value={rule.id_pregunta_origen} onChange={(e) => setRule(rule.id_regla, { id_pregunta_origen: e.target.value })}>
          {allQuestions.filter((item) => item.id_pregunta !== question.id_pregunta).map((item) => <option key={item.id_pregunta} value={item.id_pregunta}>{item.etiqueta}</option>)}
        </select></label>
        <label>Operador<select value={rule.operador} onChange={(e) => setRule(rule.id_regla, { operador: e.target.value })}>
          {OPERATORS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        {!['EMPTY', 'NOT_EMPTY'].includes(rule.operador) && <label>Valor<input value={rule.valor_comparacion ?? ''} onChange={(e) => setRule(rule.id_regla, { valor_comparacion: e.target.value })} /></label>}
        <label>Acción<select value={rule.accion} onChange={(e) => setRule(rule.id_regla, { accion: e.target.value })}>
          <option value="MOSTRAR">Mostrar pregunta</option><option value="OCULTAR">Ocultar pregunta</option>
          <option value="OBLIGATORIA">Hacer obligatoria</option><option value="OPCIONAL">Hacer opcional</option>
        </select></label>
        <label>Combinar<select value={rule.grupo} onChange={(e) => setRule(rule.id_regla, { grupo: e.target.value as FormRule['grupo'] })}>
          <option value="TODAS">Todas (Y)</option><option value="CUALQUIERA">Cualquiera (O)</option>
        </select></label>
        <button type="button" className="ghost" onClick={() => onRulesChange(rules.filter((item) => item.id_regla !== rule.id_regla))}>Eliminar condición</button>
      </div>)}
    </div>
    <div className="question-editor-actions">
      <button type="button" className="secondary" onClick={onDuplicate}>Duplicar</button>
      <button type="button" className="danger ghost-danger" onClick={onDelete}>Eliminar</button>
    </div>
  </article>;
}
