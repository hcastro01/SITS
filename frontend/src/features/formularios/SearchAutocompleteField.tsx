import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { searchFormOptions, type SearchResult } from '../../api/formBuilder';

const DEBOUNCE_MS = 350;
const MAX_LOCAL_RESULTS = 50;

function normalize(value: string): string {
  return value.trim().normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase('es');
}

function labelForValue(value: string, options?: SearchResult[]): string {
  return options?.find((option) => option.id === value)?.label ?? value;
}

export function SearchAutocompleteField({ id, source, options, catalogType, value, placeholder,
  ariaLabel, required, disabled, selectionOnly = false, onSelect }: {
  id?: string;
  source?: string;
  options?: SearchResult[];
  catalogType?: string;
  value: string;
  placeholder?: string;
  ariaLabel?: string;
  required?: boolean;
  disabled?: boolean;
  selectionOnly?: boolean;
  onSelect: (result: SearchResult | null, text: string) => void;
}) {
  const generatedListId = useId();
  const listId = `${id ?? generatedListId}-options`;
  const rootRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const requestNumber = useRef(0);
  const resolutionNumber = useRef(0);
  const selectedValue = useRef<string | null>(null);
  const committedLabel = useRef(labelForValue(value, options));
  const propagatedValue = useRef<string | null>(null);
  const previousValue = useRef(value);
  const blurTimer = useRef<number | null>(null);
  const [query, setQuery] = useState(() => labelForValue(value, options));
  const [searchTerm, setSearchTerm] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [loadError, setLoadError] = useState(false);
  const [dropAbove, setDropAbove] = useState(false);

  useEffect(() => {
    if (value === previousValue.current) return;
    previousValue.current = value;
    if (value === propagatedValue.current) {
      propagatedValue.current = null;
      return;
    }
    if (value === selectedValue.current) return;
    selectedValue.current = null;
    committedLabel.current = labelForValue(value, options);
    setQuery(committedLabel.current);
    setSearchTerm(null);
    setOpen(false);
    inputRef.current?.setCustomValidity('');
  }, [value, options]);

  useEffect(() => () => {
    requestNumber.current += 1;
    resolutionNumber.current += 1;
    if (blurTimer.current !== null) window.clearTimeout(blurTimer.current);
  }, []);

  useEffect(() => {
    const current = ++resolutionNumber.current;
    if (!selectionOnly || options || !source || !value || selectedValue.current === value) return;
    searchFormOptions(source, '', catalogType, false, value)
      .then((items) => {
        const resolved = items.find((item) => item.id === value);
        if (current === resolutionNumber.current && resolved) {
          committedLabel.current = resolved.label;
          setQuery(resolved.label);
        }
      })
      .catch(() => undefined);
  }, [value, source, catalogType, options, selectionOnly]);

  function localResults(term: string, browse: boolean): SearchResult[] {
    if (!options) return [];
    const normalized = normalize(term);
    const matches = browse || !normalized
      ? options
      : options.filter((option) => normalize(option.label).includes(normalized));
    return matches.slice(0, MAX_LOCAL_RESULTS);
  }

  async function findResults(term: string, browse: boolean, activate: 'first' | 'last' | null = null) {
    const current = ++requestNumber.current;
    setActive(-1);
    setOpen(true);
    setLoadError(false);
    if (options) {
      const items = localResults(term, browse);
      setResults(items);
      if (activate && items.length) setActive(activate === 'first' ? 0 : items.length - 1);
      setLoading(false);
      return;
    }
    if (!source) {
      setResults([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      const items = await searchFormOptions(source, browse ? '' : term, catalogType, browse);
      if (current === requestNumber.current) {
        setResults(items);
        if (activate && items.length) setActive(activate === 'first' ? 0 : items.length - 1);
      }
    } catch {
      if (current === requestNumber.current) {
        setResults([]);
        setLoadError(true);
      }
    } finally {
      if (current === requestNumber.current) setLoading(false);
    }
  }

  useEffect(() => {
    if (searchTerm === null || disabled) return;
    const term = searchTerm.trim();
    if (term.length < 2) {
      requestNumber.current += 1;
      setResults([]);
      setLoading(false);
      setOpen(false);
      return;
    }
    const timer = window.setTimeout(() => { void findResults(term, false); }, DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
  }, [searchTerm, source, catalogType, disabled, options]);

  function close() {
    requestNumber.current += 1;
    setLoading(false);
    setOpen(false);
    setActive(-1);
    setLoadError(false);
  }

  function choose(result: SearchResult) {
    resolutionNumber.current += 1;
    selectedValue.current = result.id;
    committedLabel.current = result.label;
    propagatedValue.current = null;
    setQuery(result.label);
    setSearchTerm(null);
    setOpen(false);
    setActive(-1);
    inputRef.current?.setCustomValidity('');
    onSelect(result, result.label);
  }

  function toggle() {
    if (open) { close(); return; }
    setSearchTerm(null);
    void findResults('', true);
  }

  function handleBlur() {
    blurTimer.current = window.setTimeout(() => {
      if (!rootRef.current?.contains(document.activeElement)) {
        close();
        if (selectionOnly) {
          propagatedValue.current = null;
          setQuery(value ? committedLabel.current : '');
          setSearchTerm(null);
          inputRef.current?.setCustomValidity('');
        }
      }
    }, 0);
  }

  useLayoutEffect(() => {
    if (!open) { setDropAbove(false); return; }
    function reposition() {
      const root = rootRef.current?.getBoundingClientRect();
      const list = listRef.current;
      if (!root || !list) return;
      const listHeight = Math.min(list.scrollHeight, 240);
      const spaceBelow = window.innerHeight - root.bottom;
      setDropAbove(spaceBelow < listHeight + 8 && root.top > spaceBelow);
    }
    const frame = window.requestAnimationFrame(reposition);
    window.addEventListener('resize', reposition);
    window.addEventListener('scroll', reposition, true);
    return () => {
      window.cancelAnimationFrame(frame);
      window.removeEventListener('resize', reposition);
      window.removeEventListener('scroll', reposition, true);
    };
  }, [open, results.length, loading, loadError]);

  return (
    <div ref={rootRef} className="autocomplete" onBlur={handleBlur}>
      <input
        ref={inputRef} id={id} role="combobox" aria-label={ariaLabel} aria-autocomplete="list" aria-haspopup="listbox"
        aria-expanded={open} aria-controls={listId} aria-busy={loading || undefined}
        aria-activedescendant={open && active >= 0 ? `${listId}-${active}` : undefined}
        value={query} placeholder={placeholder ?? 'Escriba para buscar…'} required={required} disabled={disabled}
        onChange={(event) => {
          const next = event.target.value;
          resolutionNumber.current += 1;
          selectedValue.current = null;
          if (!next) committedLabel.current = '';
          propagatedValue.current = next;
          if (selectionOnly) event.currentTarget.setCustomValidity(next ? 'Seleccione una opción de la lista.' : '');
          setQuery(next);
          setSearchTerm(next);
          onSelect(null, next);
        }}
        onKeyDown={(event) => {
          if (event.key === 'Escape') { if (open) event.preventDefault(); close(); return; }
          if (event.key === 'ArrowDown') {
            event.preventDefault();
            if (!open) { setSearchTerm(null); void findResults('', true, 'first'); return; }
            if (results.length) setActive((current) => Math.min(current + 1, results.length - 1));
          }
          if (event.key === 'ArrowUp' && !open) {
            event.preventDefault();
            setSearchTerm(null);
            void findResults('', true, 'last');
            return;
          }
          if (event.key === 'ArrowUp' && results.length) {
            event.preventDefault();
            setActive((current) => current <= 0 ? results.length - 1 : current - 1);
          }
          if (event.key === 'Enter' && open && active >= 0 && results[active]) {
            event.preventDefault();
            choose(results[active]);
          }
        }}
      />
      {loading && <span className="autocomplete-status" role="status">Buscando…</span>}
      <button type="button" className="autocomplete-toggle" disabled={disabled} aria-expanded={open}
        aria-controls={listId} aria-label={`${open ? 'Cerrar' : 'Mostrar'} opciones${ariaLabel ? ` de ${ariaLabel}` : ''}`}
        onMouseDown={(event) => event.preventDefault()} onClick={toggle}
        onKeyDown={(event) => { if (event.key === 'Escape' && open) { event.preventDefault(); close(); } }}>
        <span aria-hidden="true">▾</span>
      </button>
      {open && (
        <ul ref={listRef} id={listId}
          className={`autocomplete-results${dropAbove ? ' autocomplete-results--above' : ''}`} role="listbox"
          aria-label={ariaLabel ? `Opciones de ${ariaLabel}` : 'Opciones'}>
          {loadError && !loading
            ? <li className="autocomplete-empty">No fue posible cargar las opciones. Escriba para reintentar.</li>
            : results.length === 0 && !loading
            ? <li className="autocomplete-empty">No se encontraron coincidencias.</li>
            : results.map((result, index) => (
              <li key={result.id} id={`${listId}-${index}`} role="option" aria-selected={active === index}
                  className={active === index ? 'is-active' : ''} onMouseEnter={() => setActive(index)}
                  onMouseDown={(event) => event.preventDefault()} onClick={() => choose(result)}>
                {result.label}
              </li>
            ))}
        </ul>
      )}
    </div>
  );
}
