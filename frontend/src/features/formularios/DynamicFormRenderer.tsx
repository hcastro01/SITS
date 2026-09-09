import { useMemo } from 'react';
import type { FormDefinition, FormQuestion, FormRule, SearchResult } from '../../api/formBuilder';
import { SearchAutocompleteField } from './SearchAutocompleteField';

export type FieldValue = string | string[] | boolean | File[];
export type FormValues = Record<string, FieldValue>;

function text(value: FieldValue | undefined): string {
  return typeof value === 'string' ? value : '';
}

function matches(rule: FormRule, value: FieldValue | undefined): boolean {
  const values = Array.isArray(value) && !value.some((item) => item instanceof File) ? value as string[] : [value];
  const normalized = values.filter((item) => item !== undefined).map((item) => String(item).toLowerCase());
  const expected = String(rule.valor_comparacion ?? '').toLowerCase();
  if (rule.operador === 'EMPTY') return normalized.length === 0 || normalized.every((item) => !item);
  if (rule.operador === 'NOT_EMPTY') return normalized.some(Boolean);
  if (rule.operador === 'INCLUDES') return normalized.includes(expected);
  if (rule.operador === 'NOT_INCLUDES') return !normalized.includes(expected);
  const current = normalized[0] ?? '';
  if (rule.operador === 'EQ') return current === expected;
  if (rule.operador === 'NE') return current !== expected;
  if (rule.operador === 'CONTAINS') return current.includes(expected);
  if (rule.operador === 'NOT_CONTAINS') return !current.includes(expected);
  const left = Number(current); const right = Number(expected);
  if (!Number.isFinite(left) || !Number.isFinite(right)) return false;
  return rule.operador === 'GT' ? left > right : rule.operador === 'GTE' ? left >= right :
    rule.operador === 'LT' ? left < right : rule.operador === 'LTE' ? left <= right : false;
}

export function computeDynamicState(definition: FormDefinition, values: FormValues) {
  const visibleQuestions = Object.fromEntries(definition.preguntas.map((q) => [q.id_pregunta, q.visible !== false]));
  const requiredQuestions = Object.fromEntries(definition.preguntas.map((q) => [q.id_pregunta, q.obligatoria]));
  const visibleSections = Object.fromEntries(definition.secciones.map((s) => [s.id_seccion, true]));
  const groups = new Map<string, { rule: FormRule; results: boolean[] }>();
  definition.reglas.forEach((rule) => {
    const key = [rule.id_pregunta_destino, rule.id_seccion_destino, rule.accion, rule.grupo].join('|');
    const group = groups.get(key) ?? { rule, results: [] };
    group.results.push(matches(rule, values[rule.id_pregunta_origen])); groups.set(key, group);
  });
  groups.forEach(({ rule, results }) => {
    const active = rule.grupo === 'CUALQUIERA' ? results.some(Boolean) : results.every(Boolean);
    if (rule.accion === 'MOSTRAR' && rule.id_pregunta_destino) visibleQuestions[rule.id_pregunta_destino] = active;
    if (rule.accion === 'OCULTAR' && active && rule.id_pregunta_destino) visibleQuestions[rule.id_pregunta_destino] = false;
    if (rule.accion === 'OBLIGATORIA' && rule.id_pregunta_destino) requiredQuestions[rule.id_pregunta_destino] = active;
    if (rule.accion === 'OPCIONAL' && active && rule.id_pregunta_destino) requiredQuestions[rule.id_pregunta_destino] = false;
    if (rule.accion === 'MOSTRAR_SECCION' && rule.id_seccion_destino) visibleSections[rule.id_seccion_destino] = active;
    if (rule.accion === 'OCULTAR_SECCION' && active && rule.id_seccion_destino) visibleSections[rule.id_seccion_destino] = false;
  });
  definition.preguntas.forEach((question) => {
    if (question.id_seccion && visibleSections[question.id_seccion] === false) visibleQuestions[question.id_pregunta] = false;
  });
  return { visibleQuestions, requiredQuestions, visibleSections };
}

function DynamicField({ question, value, required, disabled, onChange, onAutocomplete }: {
  question: FormQuestion; value: FieldValue | undefined; required: boolean; disabled: boolean;
  onChange: (value: FieldValue) => void; onAutocomplete: (result: SearchResult | null, label: string) => void;
}) {
  const config = question.configuracion ?? {};
  const validation = question.validacion ?? {};
  const common = { id: question.id_pregunta, required, disabled,
    placeholder: String(config.placeholder ?? ''), minLength: Number(validation.min_length) || undefined,
    maxLength: Number(validation.max_length ?? question.longitud_maxima) || undefined };
  if (question.tipo === 'TEXTO_LARGO') return <textarea {...common} value={text(value)} onChange={(e) => onChange(e.target.value)} />;
  if (['NUMERO', 'NUMERO_ENTERO', 'NUMERO_DECIMAL', 'MONEDA', 'PORCENTAJE'].includes(question.tipo)) {
    const step = question.tipo === 'NUMERO_ENTERO' ? 1 : question.tipo === 'PORCENTAJE' ? .01 : 'any';
    return <input {...common} type="number" step={step} min={String(validation.min ?? '') || undefined}
      max={String(validation.max ?? '') || undefined} value={text(value)} onChange={(e) => onChange(e.target.value)} />;
  }
  if (question.tipo === 'FECHA') return <input {...common} type="date" value={text(value)} onChange={(e) => onChange(e.target.value)} />;
  if (question.tipo === 'HORA') return <input {...common} type="time" value={text(value)} onChange={(e) => onChange(e.target.value)} />;
  if (question.tipo === 'FECHA_HORA') return <input {...common} type="datetime-local" value={text(value)} onChange={(e) => onChange(e.target.value)} />;
  if (question.tipo === 'EMAIL') return <input {...common} type="email" value={text(value)} onChange={(e) => onChange(e.target.value)} />;
  if (question.tipo === 'TELEFONO') return <input {...common} type="tel" value={text(value)} onChange={(e) => onChange(e.target.value)} />;
  if (question.tipo === 'SI_NO') return <div className="choice-group">
    {['Sí', 'No'].map((label) => <label key={label}><input type="radio" name={question.id_pregunta} value={label}
      checked={text(value) === label} required={required} disabled={disabled} onChange={() => onChange(label)} /> {label}</label>)}
  </div>;
  if (question.tipo === 'SELECCION_UNICA') return <div className="choice-group">
    {question.opciones.map((option) => <label key={option.id_opcion}><input type="radio" name={question.id_pregunta}
      value={option.valor} checked={text(value) === option.valor} required={required} disabled={disabled}
      onChange={() => onChange(option.valor)} /> {option.etiqueta}</label>)}
  </div>;
  if (question.tipo === 'LISTA_DESPLEGABLE') {
    if (question.opciones.length <= 12) return <select id={question.id_pregunta} value={text(value)}
      required={required} disabled={disabled} onChange={(event) => onChange(event.target.value)}>
      <option value="">Seleccione…</option>
      {question.opciones.map((option) => <option key={option.id_opcion} value={option.valor}>{option.etiqueta}</option>)}
    </select>;
    return <SearchAutocompleteField
      id={question.id_pregunta} ariaLabel={question.etiqueta} value={text(value)} required={required} disabled={disabled}
      placeholder={String(config.placeholder ?? 'Escriba para buscar…')}
      options={question.opciones.map((option) => ({ id: option.valor, label: option.etiqueta, data: {} }))}
      selectionOnly onSelect={(result, label) => { if (result) onChange(result.id); else if (!label) onChange(''); }} />;
  }
  if (['SELECCION_MULTIPLE', 'CASILLAS'].includes(question.tipo)) {
    const selected = Array.isArray(value) ? value as string[] : [];
    return <div className="choice-group">{question.opciones.map((option) => <label key={option.id_opcion}>
      <input type="checkbox" checked={selected.includes(option.valor)} disabled={disabled} onChange={(e) =>
        onChange(e.target.checked ? [...selected, option.valor] : selected.filter((item) => item !== option.valor))} /> {option.etiqueta}
    </label>)}</div>;
  }
  if (['ESCALA', 'CALIFICACION'].includes(question.tipo)) {
    const minimum = Number(config.min ?? 1); const maximum = Number(config.max ?? 5);
    return <div className="rating-field">{Array.from({ length: Math.min(maximum - minimum + 1, 10) }, (_, i) => minimum + i).map((number) =>
      <label key={number}><input type="radio" name={question.id_pregunta} value={number} checked={text(value) === String(number)}
        required={required} disabled={disabled} onChange={() => onChange(String(number))} /><span>{number}</span></label>)}</div>;
  }
  if (question.tipo === 'BUSQUEDA') return <SearchAutocompleteField
    id={question.id_pregunta} ariaLabel={question.etiqueta} source={question.fuente_datos ?? 'PERSONAS'}
    catalogType={typeof config.catalog_type === 'string' ? config.catalog_type : undefined}
    value={text(value)} placeholder={String(config.placeholder ?? 'Escriba para buscar…')}
    required={required} disabled={disabled} selectionOnly onSelect={onAutocomplete} />;
  if (['ARCHIVO', 'FOTOGRAFIA'].includes(question.tipo)) {
    const rawItems = Array.isArray(value) ? value : [];
    const files = rawItems.filter((item): item is File => item instanceof File);
    const savedFiles = rawItems.filter((item) => typeof item === 'string');
    if (disabled && savedFiles.length > 0) return <p className="readonly-value">{savedFiles.length === 1 ? '1 archivo asociado' : `${savedFiles.length} archivos asociados`}</p>;
    return <div className="file-field"><input id={question.id_pregunta} type="file" required={required && files.length === 0}
      disabled={disabled} multiple={Number(config.max_files ?? 1) > 1}
      accept={question.tipo === 'FOTOGRAFIA' ? 'image/jpeg,image/png,image/webp' : String(config.accept ?? '.pdf,.doc,.docx,.xls,.xlsx,.jpg,.jpeg,.png,.webp')}
      capture={question.tipo === 'FOTOGRAFIA' ? 'environment' : undefined}
      onChange={(e) => onChange(Array.from(e.target.files ?? []))} />
      {files.length > 0 && <ul className="selected-files">{files.map((file) => <li key={`${file.name}-${file.size}`}>{file.name}</li>)}</ul>}
      {question.tipo === 'FOTOGRAFIA' && files[0] && <img className="image-preview" src={URL.createObjectURL(files[0])} alt="Vista previa seleccionada" />}
    </div>;
  }
  return <input {...common} type="text" value={text(value)} onChange={(e) => onChange(e.target.value)} />;
}

export function DynamicFormRenderer({ definition, values, onChange, readOnly = false }: {
  definition: FormDefinition; values: FormValues; onChange: (values: FormValues) => void; readOnly?: boolean;
}) {
  const state = useMemo(() => computeDynamicState(definition, values), [definition, values]);
  const update = (questionId: string, value: FieldValue) => onChange({ ...values, [questionId]: value });
  const renderQuestion = (question: FormQuestion) => {
    if (!state.visibleQuestions[question.id_pregunta]) return null;
    if (question.tipo === 'TITULO') return <h3 key={question.id_pregunta}>{question.etiqueta}</h3>;
    if (question.tipo === 'INFORMATIVO') return <p key={question.id_pregunta} className="form-information"><strong>{question.etiqueta}</strong>{question.descripcion && <><br />{question.descripcion}</>}</p>;
    const required = Boolean(state.requiredQuestions[question.id_pregunta]);
    return <div className="dynamic-field" key={question.id_pregunta}>
      <label htmlFor={question.id_pregunta}>{question.etiqueta}{required && <span aria-hidden="true"> *</span>}</label>
      {question.descripcion && <p>{question.descripcion}</p>}
      <DynamicField question={question} value={values[question.id_pregunta]} required={required}
        disabled={readOnly || question.solo_lectura} onChange={(value) => update(question.id_pregunta, value)}
        onAutocomplete={(result, label) => {
          if (!result && label) return;
          const next = { ...values, [question.id_pregunta]: result?.id ?? '' };
          if (result) Object.entries(question.mapping ?? {}).forEach(([sourceField, targetId]) => {
            if (targetId && result.data[sourceField] != null) next[targetId] = String(result.data[sourceField]);
          });
          else Object.values(question.mapping ?? {}).forEach((targetId) => {
            if (targetId) next[targetId] = '';
          });
          onChange(next);
        }} />
      {question.texto_ayuda && <small>{question.texto_ayuda}</small>}
    </div>;
  };
  const unsectioned = definition.preguntas.filter((q) => !q.id_seccion);
  return <div className="dynamic-form-renderer">
    {unsectioned.map(renderQuestion)}
    {definition.secciones.map((section) => state.visibleSections[section.id_seccion] !== false && (
      <section className="dynamic-section" key={section.id_seccion}>
        <div className="dynamic-section-heading"><h3>{section.titulo}</h3>{section.descripcion && <p>{section.descripcion}</p>}</div>
        {definition.preguntas.filter((q) => q.id_seccion === section.id_seccion).map(renderQuestion)}
      </section>
    ))}
  </div>;
}
