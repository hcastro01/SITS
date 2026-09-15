import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { canAccess } from '../../api/auth';
import { HttpError } from '../../api/client';
import { listDestinationTree, listFormDefinitions, type FormDestinationNode } from '../../api/formBuilder';
import { useAuth } from '../../app/AuthContext';
import { destinationPaths } from './HierarchicalDestinationPicker';

export interface ContextualFormsConfig {
  label: string;
  processCode: string;
  subprocessCodes: readonly string[];
}

export const CONTEXTUAL_FORM_BRANCHES = {
  activities: { label: 'Actividades', processCode: 'ACTIVIDADES', subprocessCodes: ['GENERAL'] },
  medical: { label: 'Departamento Médico', processCode: 'DEPARTAMENTO_MEDICO', subprocessCodes: ['RIESGOS_TRABAJO', 'AUSENTISMOS', 'ACCIDENTES'] },
  production: { label: 'Producción', processCode: 'PRODUCCION', subprocessCodes: ['ATENCIONES', 'RECORRIDOS', 'NOVEDADES_PLANTA'] },
  office: { label: 'Oficina', processCode: 'OFICINA', subprocessCodes: ['BENEFICIOS', 'ATENCIONES', 'PRESTAMOS', 'SEGURO'] },
} as const satisfies Record<string, ContextualFormsConfig>;

function findByCode(nodes: FormDestinationNode[], code: string): FormDestinationNode | undefined {
  for (const node of nodes) {
    if (node.codigo === code) return node;
    const child = findByCode(node.hijos, code);
    if (child) return child;
  }
  return undefined;
}

export function ContextualFormsPage({ config }: { config: ContextualFormsConfig }) {
  const { usuario } = useAuth();
  const canEdit = canAccess(usuario, 'FORMULARIOS', 'edit');
  const [tree, setTree] = useState<FormDestinationNode[]>([]);
  const [forms, setForms] = useState<Awaited<ReturnType<typeof listFormDefinitions>>>([]);
  const [selectedCode, setSelectedCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true); setError(null);
    Promise.all([listDestinationTree(), listFormDefinitions()])
      .then(([catalog, definitions]) => { if (active) { setTree(catalog); setForms(definitions); } })
      .catch((err: unknown) => { if (active) setError(err instanceof HttpError ? err.message : 'No fue posible cargar los formularios de esta rama.'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  const branch = useMemo(() => findByCode(tree, config.processCode), [tree, config.processCode]);
  const subprocesses = useMemo(() => {
    if (!branch) return [];
    return config.subprocessCodes.map((code) => branch.hijos.find((node) => node.codigo === code)).filter((node): node is FormDestinationNode => Boolean(node));
  }, [branch, config.subprocessCodes]);
  const allowedIds = useMemo(() => new Set(subprocesses.map((node) => node.id_destino)), [subprocesses]);
  const visibleForms = useMemo(() => forms.filter((form) => (form.destinos_jerarquicos ?? []).some((id) => allowedIds.has(id) && (!selectedCode || id === subprocesses.find((node) => node.codigo === selectedCode)?.id_destino))), [forms, allowedIds, selectedCode, subprocesses]);
  const paths = useMemo(() => destinationPaths(tree), [tree]);
  const unavailableBranch = !loading && !error && (!branch || subprocesses.length !== config.subprocessCodes.length);

  return <section className="forms-admin-page contextual-forms-page">
    <section className="panel forms-heading"><div><p className="eyebrow">Trabajo Social · {config.label}</p><h2>Formularios</h2><p>Plantillas del Repositorio central asignadas explícitamente a esta rama.</p></div><Link className="button-link" to="/formularios">Ir al Repositorio central</Link></section>
    {error && <p className="form-error" role="alert">{error}</p>}
    {loading ? <p className="loading-message">Cargando formularios…</p> : unavailableBranch ? <p className="form-error" role="alert">No fue posible resolver la rama autorizada en el catálogo de destinos.</p> : <>
      <section className="record-filters" aria-label="Filtro de subproceso"><label>Subproceso<select value={selectedCode} onChange={(event) => setSelectedCode(event.target.value)}><option value="">Todos</option>{subprocesses.map((node) => <option key={node.id_destino} value={node.codigo}>{node.nombre}</option>)}</select></label></section>
      {visibleForms.length === 0 ? <div className="panel empty-state"><strong>No hay formularios asignados a esta rama.</strong><p>Los destinos textuales históricos y las asignaciones a otros procesos no se incluyen aquí.</p></div> : <div className="form-cards">{visibleForms.map((form) => <article className="form-card" key={form.id_formulario}><div className="form-card-top"><span className={`badge status-${form.estado.toLowerCase()}`}>{form.estado}</span></div><h3>{form.nombre}</h3><p>{form.descripcion || 'Sin descripción.'}</p><div className="form-destinations">{(form.destinos_jerarquicos ?? []).filter((id) => allowedIds.has(id)).map((id) => <span key={id}>{paths.get(id) ?? id}</span>)}</div><dl className="form-metrics"><div><dt>Preguntas</dt><dd>{form.total_preguntas}</dd></div><div><dt>Respuestas</dt><dd>{form.total_respuestas}</dd></div><div><dt>Versión</dt><dd>{form.version_publicada || '—'}</dd></div></dl><div className="form-card-actions"><Link className="secondary button-link" to="/formularios">Consultar en Repositorio central</Link>{canEdit && <Link className="button-link" to={`/formularios/${form.id_formulario}`}>Administrar formulario</Link>}</div></article>)}</div>}
    </>}
  </section>;
}
