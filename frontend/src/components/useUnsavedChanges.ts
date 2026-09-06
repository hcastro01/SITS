import { useCallback, useEffect } from 'react';
import { useBlocker } from 'react-router-dom';
import { useFeedback } from './FeedbackProvider';

const MESSAGE = 'Tienes cambios sin guardar. ¿Deseas salir sin guardar?';

export function useUnsavedChanges(isDirty: boolean) {
  const { confirm } = useFeedback();
  const blocker = useBlocker(isDirty);

  useEffect(() => {
    if (blocker.state !== 'blocked') return;
    void confirm({
      title: 'Cambios sin guardar',
      message: MESSAGE,
      confirmLabel: 'Salir sin guardar',
      cancelLabel: 'Continuar editando',
      danger: true,
    }).then((accepted) => accepted ? blocker.proceed() : blocker.reset());
  }, [blocker, confirm]);

  useEffect(() => {
    if (!isDirty) return;
    const beforeUnload = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener('beforeunload', beforeUnload);
    return () => window.removeEventListener('beforeunload', beforeUnload);
  }, [isDirty]);

  return useCallback(async (onLeave: () => void) => {
    if (!isDirty || await confirm({
      title: 'Cambios sin guardar',
      message: MESSAGE,
      confirmLabel: 'Salir sin guardar',
      cancelLabel: 'Continuar editando',
      danger: true,
    })) onLeave();
  }, [confirm, isDirty]);
}
