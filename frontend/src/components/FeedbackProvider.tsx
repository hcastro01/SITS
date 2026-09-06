import { createContext, useCallback, useContext, useRef, useState, type ReactNode } from 'react';
import { Modal } from './Modal';

type ToastTone = 'success' | 'error' | 'info';

interface Toast {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ConfirmOptions {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
}

interface FeedbackContextValue {
  notify: (message: string, tone?: ToastTone) => void;
  confirm: (options: ConfirmOptions) => Promise<boolean>;
}

const FeedbackContext = createContext<FeedbackContextValue | null>(null);

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [confirmation, setConfirmation] = useState<ConfirmOptions | null>(null);
  const resolver = useRef<((accepted: boolean) => void) | null>(null);
  const nextId = useRef(1);

  const notify = useCallback((message: string, tone: ToastTone = 'success') => {
    const id = nextId.current++;
    setToasts((current) => [...current, { id, message, tone }]);
    window.setTimeout(() => setToasts((current) => current.filter((toast) => toast.id !== id)), 4500);
  }, []);

  const confirm = useCallback((options: ConfirmOptions) => new Promise<boolean>((resolve) => {
    resolver.current = resolve;
    setConfirmation(options);
  }), []);

  function settle(accepted: boolean) {
    resolver.current?.(accepted);
    resolver.current = null;
    setConfirmation(null);
  }

  return (
    <FeedbackContext.Provider value={{ notify, confirm }}>
      {children}
      <div className="toast-region" aria-live="polite" aria-atomic="false">
        {toasts.map((toast) => (
          <div key={toast.id} className={`toast toast--${toast.tone}`} role={toast.tone === 'error' ? 'alert' : 'status'}>
            <span aria-hidden="true">{toast.tone === 'success' ? '✓' : toast.tone === 'error' ? '!' : 'i'}</span>
            <p>{toast.message}</p>
            <button type="button" onClick={() => setToasts((current) => current.filter((item) => item.id !== toast.id))} aria-label="Cerrar mensaje">×</button>
          </div>
        ))}
      </div>
      {confirmation && (
        <Modal titulo={confirmation.title} onClose={() => settle(false)} size="small">
          <p className="dialog-message">{confirmation.message}</p>
          <div className="modal-actions">
            <button type="button" className="secondary" onClick={() => settle(false)}>
              {confirmation.cancelLabel ?? 'Cancelar'}
            </button>
            <button type="button" className={confirmation.danger ? 'danger' : undefined} onClick={() => settle(true)}>
              {confirmation.confirmLabel ?? 'Confirmar'}
            </button>
          </div>
        </Modal>
      )}
    </FeedbackContext.Provider>
  );
}

export function useFeedback(): FeedbackContextValue {
  const context = useContext(FeedbackContext);
  if (!context) throw new Error('useFeedback debe usarse dentro de <FeedbackProvider>.');
  return context;
}
