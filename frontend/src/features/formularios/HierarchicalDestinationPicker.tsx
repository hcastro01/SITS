import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { HttpError } from '../../api/client';
import {
  listDestinationTree, listFormDestinations, syncFormDestinations,
  type FormDestinationNode,
} from '../../api/formBuilder';
import { useFeedback } from '../../components/FeedbackProvider';

export function destinationPaths(tree: FormDestinationNode[]): Map<string, string> {
  const result = new Map<string, string>();
  const visit = (node: FormDestinationNode, path: string[]) => {
    const next = [...path, node.nombre];
    result.set(node.id_destino, next.join(' / '));
    node.hijos.forEach((child) => visit(child, next));
  };
  tree.forEach((node) => visit(node, []));
  return result;
}

export function HierarchicalDestinationPicker({ formId, canEdit, onSaved }: {
  formId: string; canEdit: boolean; onSaved?: (ids: string[]) => void;
}) {
  const { notify } = useFeedback();
  const [tree, setTree] = useState<FormDestinationNode[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [catalog, assignments] = await Promise.all([listDestinationTree(), listFormDestinations(formId)]);
      setTree(catalog); setSelected(assignments.map((item) => item.id_destino_catalogo));
    } catch (err) { setError(err instanceof HttpError ? err.message : 'No fue posible cargar los destinos.'); }
    finally { setLoading(false); }
  }, [formId]);
  useEffect(() => { void load(); }, [load]);
  const saved = useMemo(() => selected.join('|'), [selected]);

  async function save() {
    if (saving || !canEdit) return;
    setSaving(true); setError(null);
    try {
      const assignments = await syncFormDestinations(formId, selected);
      const ids = assignments.map((item) => item.id_destino_catalogo);
      setSelected(ids); onSaved?.(ids); notify('Destinos jerárquicos guardados.');
    } catch (err) { setError(err instanceof HttpError ? err.message : 'No fue posible guardar los destinos.'); }
    finally { setSaving(false); }
  }
  function toggle(id: string, checked: boolean) {
    setSelected((current) => checked ? [...current, id] : current.filter((value) => value !== id));
  }
  function renderNode(node: FormDestinationNode, depth = 0): ReactNode {
    const leaf = node.nivel === 'SUBPROCESO';
    return <li key={node.id_destino} className={`destination-tree__node destination-tree__node--${node.nivel.toLowerCase()}`}>
      <div style={{ paddingInlineStart: `${depth * 18}px` }}>
        {leaf ? <label><input aria-label={`Destino ${node.nombre}`} type="checkbox" disabled={!canEdit || saving} checked={selected.includes(node.id_destino)} onChange={(e) => toggle(node.id_destino, e.target.checked)} /> {node.nombre}</label> : <strong>{node.nombre}</strong>}
      </div>
      {node.hijos.length > 0 && <ul>{node.hijos.map((child) => renderNode(child, depth + 1))}</ul>}
    </li>;
  }
  if (loading) return <p className="loading-message">Cargando destinos jerárquicos…</p>;
  return <section className="destination-manager" aria-label="Destinos jerárquicos">
    <div><h4>Destinos jerárquicos</h4><p>Seleccione uno o varios subprocesos. La plantilla sigue siendo única.</p></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {!canEdit && <p className="footnote">No tiene permiso para modificar asignaciones de destinos.</p>}
    {tree.length === 0 ? <p className="footnote">No hay destinos activos disponibles.</p> : <ul className="destination-tree">{tree.map((node) => renderNode(node))}</ul>}
    <div className="button-row"><button type="button" disabled={!canEdit || saving || !tree.length} onClick={() => void save()}>{saving ? 'Guardando destinos…' : 'Guardar destinos'}</button>{saved === '' && <span className="footnote">Sin destinos jerárquicos asignados.</span>}</div>
  </section>;
}
