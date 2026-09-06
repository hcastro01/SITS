import { useEffect, useId, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

const FOCUSABLE = 'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

const modalStack: HTMLElement[] = [];
let bodyOverflowBeforeModals = '';

function syncModalAccessibility() {
  const top = modalStack.at(-1);
  modalStack.forEach((overlay) => {
    const isTop = overlay === top;
    overlay.inert = !isTop;
    if (isTop) overlay.removeAttribute('aria-hidden');
    else overlay.setAttribute('aria-hidden', 'true');
  });
}

export function Modal({ titulo, onClose, children, size = 'medium', closeOnBackdrop = true }: {
  titulo: string;
  onClose: () => void;
  children: ReactNode;
  size?: 'small' | 'medium' | 'large';
  closeOnBackdrop?: boolean;
}) {
  const titleId = useId();
  const dialogRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const openerRef = useRef<HTMLElement | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    openerRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = dialogRef.current;
    const first = dialog?.querySelector<HTMLElement>('[data-autofocus]')
      ?? dialog?.querySelector<HTMLElement>('input:not([type="hidden"]), select, textarea')
      ?? dialog?.querySelector<HTMLElement>('button, [href]');
    window.requestAnimationFrame(() => (first ?? dialog)?.focus());
    if (modalStack.length === 0) bodyOverflowBeforeModals = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    if (overlayRef.current) modalStack.push(overlayRef.current);
    syncModalAccessibility();

    function onKeyDown(event: KeyboardEvent) {
      if (modalStack.at(-1) !== overlayRef.current) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== 'Tab' || !dialogRef.current) return;
      const focusable = [...dialogRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)]
        .filter((element) => !element.hidden && element.getAttribute('aria-hidden') !== 'true');
      if (focusable.length === 0) {
        event.preventDefault();
        dialogRef.current.focus();
        return;
      }
      const firstElement = focusable[0];
      const lastElement = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === firstElement) {
        event.preventDefault();
        lastElement.focus();
      } else if (!event.shiftKey && document.activeElement === lastElement) {
        event.preventDefault();
        firstElement.focus();
      }
    }
    document.addEventListener('keydown', onKeyDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      const index = overlayRef.current ? modalStack.indexOf(overlayRef.current) : -1;
      if (index >= 0) modalStack.splice(index, 1);
      syncModalAccessibility();
      if (modalStack.length === 0) document.body.style.overflow = bodyOverflowBeforeModals;
      openerRef.current?.focus();
    };
  }, []);

  return createPortal(
    <div ref={overlayRef} className="modal-overlay" onMouseDown={() => closeOnBackdrop && onClose()}>
      <div ref={dialogRef} className={`modal modal--${size}`} role="dialog" aria-modal="true" aria-labelledby={titleId}
           tabIndex={-1} onMouseDown={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h2 id={titleId}>{titulo}</h2>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Cerrar">×</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>,
    document.body,
  );
}
