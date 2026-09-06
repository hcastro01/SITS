import { useState, type FormEvent } from 'react';
import { actualizarCaso, crearCaso, type Caso } from '../../api/casos';
import { HttpError } from '../../api/client';
import { Modal } from '../../components/Modal';

interface Props {
  caso?: Caso;
  onClose: () => void;
  onSaved: (caso: Caso) => void;
}

export function CasoFormModal({ caso, onClose, onSaved }: Props) {
  const editando = Boolean(caso);
  const [responsable, setResponsable] = useState(caso?.responsable ?? '');
  const [estadoCaso, setEstadoCaso] = useState(caso?.estado_caso ?? 'ABIERTO');
  const [tipoCaso, setTipoCaso] = useState(caso?.tipo_caso ?? '');
  const [prioridad, setPrioridad] = useState(caso?.prioridad ?? '');
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

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
    <Modal titulo={editando ? `Editar caso ${caso!.codigo_caso}` : 'Nuevo caso'} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <label htmlFor="responsable">Responsable</label>
        <input id="responsable" value={responsable} onChange={(e) => setResponsable(e.target.value)} />

        <label htmlFor="estado_caso">Estado</label>
        <input id="estado_caso" value={estadoCaso} onChange={(e) => setEstadoCaso(e.target.value)} />

        <label htmlFor="tipo_caso">Tipo de caso</label>
        <input id="tipo_caso" value={tipoCaso} onChange={(e) => setTipoCaso(e.target.value)} />

        <label htmlFor="prioridad">Prioridad</label>
        <input id="prioridad" value={prioridad} onChange={(e) => setPrioridad(e.target.value)} />

        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="secondary" onClick={onClose}>Cancelar</button>
          <button type="submit" disabled={enviando}>
            {enviando ? 'Guardando…' : editando ? 'Guardar cambios' : 'Crear caso'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
