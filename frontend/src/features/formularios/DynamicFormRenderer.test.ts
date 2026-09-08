import { describe, expect, it } from 'vitest';
import type { FormDefinition, FormQuestion } from '../../api/formBuilder';
import { computeDynamicState } from './DynamicFormRenderer';

function question(id: string, required = false, section: string | null = null): FormQuestion {
  return { id_pregunta: id, id_seccion: section, etiqueta: id, descripcion: null,
    tipo: 'TEXTO_CORTO', obligatoria: required, orden: 0, texto_ayuda: null,
    valor_predeterminado: null, visible: true, solo_lectura: false, longitud_maxima: null,
    validacion: {}, configuracion: {}, fuente_datos: null, mapping: {}, opciones: [] };
}

function definition(): FormDefinition {
  return { id_formulario: 'f1', nombre: 'Prueba', descripcion: null, responsable: null,
    estado: 'PUBLICADO', fecha_publicacion: null, fecha_actualizacion: null, actualizado_por: null,
    permite_multiples_respuestas: false, version_publicada: 1, version: 1,
    activo: true, eliminado: false, destinos: ['GENERAL'], total_preguntas: 3,
    total_respuestas: 0, secciones: [{ id_seccion: 's1', titulo: 'Detalle', descripcion: null, orden: 0 }],
    preguntas: [question('origen'), question('condicional', true), question('en-seccion', true, 's1')],
    reglas: [{ id_regla: 'r1', id_pregunta_origen: 'origen', operador: 'EQ', valor_comparacion: 'Sí',
      id_pregunta_destino: 'condicional', id_seccion_destino: null, accion: 'MOSTRAR', grupo: 'TODAS', orden: 0 },
    { id_regla: 'r2', id_pregunta_origen: 'origen', operador: 'EQ', valor_comparacion: 'Sí',
      id_pregunta_destino: null, id_seccion_destino: 's1', accion: 'MOSTRAR_SECCION', grupo: 'TODAS', orden: 1 }],
  };
}

describe('computeDynamicState', () => {
  it('oculta pregunta y sección condicionadas mientras no coincida el valor', () => {
    const state = computeDynamicState(definition(), { origen: 'No' });
    expect(state.visibleQuestions.condicional).toBe(false);
    expect(state.visibleSections.s1).toBe(false);
    expect(state.visibleQuestions['en-seccion']).toBe(false);
  });

  it('muestra pregunta y sección cuando la condición coincide', () => {
    const state = computeDynamicState(definition(), { origen: 'Sí' });
    expect(state.visibleQuestions.condicional).toBe(true);
    expect(state.visibleSections.s1).toBe(true);
    expect(state.visibleQuestions['en-seccion']).toBe(true);
  });
});
