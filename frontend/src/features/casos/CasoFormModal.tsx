import { useState, type FormEvent } from 'react';
import { actualizarCaso, crearCaso, type Caso } from '../../api/casos';
import { HttpError } from '../../api/client';
import { Modal } from '../../components/Modal';
import { useFeedback } from '../../components/FeedbackProvider';

interface Props {
  caso?: Caso;
  onClose: () => void;
  onSaved: (caso: Caso) => void;
}

export function CasoFormModal({ caso, onClose, onSaved }: Props) {
  const { confirm } = useFeedback();
  const editando = Boolean(caso);
  const [responsable, setResponsable] = useState(caso?.responsable ?? '');
  const [estadoCaso, setEstadoCaso] = useState(caso?.estado_caso ?? 'ABIERTO');
  const [tipoCaso, setTipoCaso] = useState(caso?.tipo_caso ?? '');
  const [prioridad, setPrioridad] = useState(caso?.prioridad ?? '');
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const dirty = responsable !== (caso?.responsable ?? '') || estadoCaso !== (caso?.estado_caso ?? 'ABIERTO')
    || tipoCaso !== (caso?.tipo_caso ?? '') || prioridad !== (caso?.prioridad ?? '');

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
      const datos = {
        responsable: responsable || undefined,
        estado_caso: estadoCaso || undefined,
        tipo_caso: tipoCaso || undefined,
        prioridad: prioridad || undefined,
      };
      const guardado = editando
        ? await actualizarCaso(caso!.id_caso, {
            ...datos, expected_version: caso!.version, motivo_auditoria: 'Edición desde el frontend',
          })
        : await crearCaso({ ...datos, motivo_auditoria: 'Apertura desde el frontend' });
      onSaved(guardado);
    } catch (err) {
      setError(err instanceof HttpError ? err.message : 'No fue posible guardar el caso.');
    } finally {
      setEnviando(false);
    }
  }

  return (
    <Modal titulo={editando ? `Editar caso ${caso!.codigo_caso}` : 'Nuevo caso'} onClose={() => void requestClose()} size="large">
      <form onSubmit={handleSubmit}>
        <div className="form-grid">
        <div>
        <label htmlFor="responsable">Responsable</label>
        <input id="responsable" value={responsable} onChange={(e) => setResponsable(e.target.value)} />
        </div><div>
        <label htmlFor="estado_caso">Estado</label>
        <input id="estado_caso" value={estadoCaso} onChange={(e) => setEstadoCaso(e.target.value)} />
        </div><div>
        <label htmlFor="tipo_caso">Tipo de caso</label>
        <input id="tipo_caso" value={tipoCaso} onChange={(e) => setTipoCaso(e.target.value)} />
        </div><div>
        <label htmlFor="prioridad">Prioridad</label>
        <input id="prioridad" value={prioridad} onChange={(e) => setPrioridad(e.target.value)} />
        </div></div>

        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={() => void requestClose()}>Cancelar</button>
          <button type="submit" disabled={enviando}>
            {enviando ? 'Guardando…' : editando ? 'Guardar cambios' : 'Crear caso'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
