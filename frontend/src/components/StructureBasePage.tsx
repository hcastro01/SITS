export function StructureBasePage({ title }: { title: string }) {
  return <section className="panel navigation-base-page" aria-labelledby="navigation-base-title">
    <p className="eyebrow">Trabajo Social</p>
    <h1 id="navigation-base-title">{title}</h1>
    <p className="footnote">Esta sección estará disponible cuando se implemente su flujo operativo.</p>
  </section>;
}
