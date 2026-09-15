import { describe, expect, it } from 'vitest';
import { activeAncestorIds, navigation } from './Layout';

describe('navegación jerárquica de SITS', () => {
  it('mantiene los macroprocesos y accesos principales requeridos', () => {
    expect(navigation.map((node) => node.label)).toEqual([
      'Trabajo Social', 'Repositorio de formularios', 'Administración',
    ]);
    expect(navigation[0].children?.map((node) => node.label)).toEqual([
      'Inicio', 'Actividades', 'Departamento Médico', 'Producción', 'Oficina',
    ]);
  });

  it('expande Trabajo Social y Producción en una ruta hija canónica', () => {
    expect(activeAncestorIds(navigation, '/trabajo-social/produccion/recorridos')).toEqual(
      new Set(['trabajo-social', 'produccion']),
    );
  });

  it('asigna una ruta propia a cada destino de la jerarquía', () => {
    const leaves = navigation.flatMap((root) => root.children?.flatMap((group) => group.children ?? [group]) ?? [root]);
    expect(leaves.filter((node) => node.id !== 'trabajo-social').every((node) => Boolean(node.to))).toBe(true);
    expect(activeAncestorIds(navigation, '/trabajo-social/oficina/seguro')).toEqual(
      new Set(['trabajo-social', 'oficina']),
    );
  });
});
