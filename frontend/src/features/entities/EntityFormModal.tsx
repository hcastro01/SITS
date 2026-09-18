import { useState, type FormEvent } from 'react';
import { HttpError } from '../../api/client';
import type { EntityRecord } from '../../api/entities';
import { Modal } from '../../components/Modal';
import { useFeedback } from '../../components/FeedbackProvider';
import type { EntityPageConfig } from './EntityConfig';
import { SearchAutocompleteField } from '../formularios/SearchAutocompleteField';

interface Props {
  config: EntityPageConfig;
  registro?: EntityRecord;
  onClose: () => void;
  onSaved: (registro: EntityRecord) => void;
}

export function EntityFormModal({ config, registro, onClose, onSaved }: Props) {
  const { confirm } = useFeedback();
  const editando = Boolean(registro);
  const camposFormulario = config.campos.filter((campo) => campo.enFormulario !== false);
  const [valores, setValores] = useState<Record<string, string>>(() => {
    const iniciales: Record<string, string> = {};
    for (const campo of camposFormulario) {
      const valorActual = registro?.[campo.nombre];
      if (valorActual != null) iniciales[campo.nombre] = String(valorActual);
    }
    return iniciales;
  });
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const personaIdField = config.personaIdField ?? 'id_persona';
  const [personaId, setPersonaId] = useState(() => String(registro?.[personaIdField] ?? ''));
  const [personaTexto, setPersonaTexto] = useState(() => String(registro?.persona ?? ''));
  const dirty = camposFormulario.some((campo) => (valores[campo.nombre] ?? '') !== String(registro?.[campo.nombre] ?? ''));

  async function requestClose() {
    if (!dirty || await confirm({
      title: 'Cambios sin guardar', message: 'Tienes cambios sin guardar. ¿Deseas salir sin guardar?',
      confirmLabel: 'Salir sin guardar', cancelLabel: 'Continuar editando', danger: true,
    })) onClose();
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const datos: Record<string, unknown> = {
        motivo_auditoria: editando
          ? `Edición de ${config.tituloSingular} desde el frontend`
          : `Alta de ${config.tituloSingular} desde el frontend`,
      };
      for (const campo of camposFormulario) {
        if (valores[campo.nombre]) datos[campo.nombre] = valores[campo.nombre];
      }
      if (config.personaIdField) datos[personaIdField] = personaId || null;
      else if (config.contextual && personaId) datos.id_persona = personaId;
      const guardado = editando
        ? await config.api.update(String(registro![config.api.idField]), { ...datos, expected_version: registro!.version })
        : await config.api.create(datos);
      onSaved(guardado);
    } catch (err) {
      setError(err instanceof HttpError ? err.message : `No fue posible guardar ${config.tituloSingular}.`);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Modal titulo={editando ? `Editar ${config.tituloSingular}` : `Nuevo registro: ${config.tituloSingular}`} onClose={() => void requestClose()} size="large">
      <form className="module-form" onSubmit={handleSubmit}>
        <div className="form-grid module-form-grid">
        {config.contextual && <div className="module-form-field"><label>Persona (opcional)</label><SearchAutocompleteField source="PERSONAS" value={personaTexto} ariaLabel="Persona" placeholder="Buscar por nombre o cédula" onSelect={(result, text) => { setPersonaId(result?.id ?? ''); setPersonaTexto(text); }} />{config.personaIdField && personaId && <button type="button" className="secondary" onClick={() => { setPersonaId(''); setPersonaTexto(''); }}>Limpiar Persona</button>}<small>Al seleccionarla se mostrará su nombre, cédula y área actual.</small></div>}
        {camposFormulario.map((campo) => (
          <div className="module-form-field" key={campo.nombre}>
            <label htmlFor={campo.nombre}>{campo.etiqueta}</label>
            {campo.tipo === 'select'
              ? <select id={campo.nombre} required={campo.requerido} value={valores[campo.nombre] ?? ''} onChange={(event) => setValores((previo) => ({ ...previo, [campo.nombre]: event.target.value }))}><option value="">Seleccione una opción</option>{campo.opciones?.map((opcion) => <option key={opcion} value={opcion}>{opcion}</option>)}</select>
              : <input id={campo.nombre} type={campo.tipo === 'fecha' ? 'date' : 'text'} required={campo.requerido} value={valores[campo.nombre] ?? ''} onChange={(event) => setValores((previo) => ({ ...previo, [campo.nombre]: event.target.value }))} />}
          </div>
        ))}
        </div>
        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={() => void requestClose()}>Cancelar</button>
          <button type="submit" disabled={enviando}>
            {enviando ? 'Guardando…' : editando ? 'Guardar cambios' : `Crear ${config.tituloSingular}`}
          </button>
        </div>
      </form>
    </Modal>
  );
}
