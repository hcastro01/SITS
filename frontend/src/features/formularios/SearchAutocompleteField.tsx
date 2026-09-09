import { useEffect, useId, useRef, useState } from 'react';
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
  const requestNumber = useRef(0);
  const selectedValue = useRef<string | null>(null);
  const propagatedValue = useRef<string | null>(null);
  const previousValue = useRef(value);
  const blurTimer = useRef<number | null>(null);
  const [query, setQuery] = useState(() => labelForValue(value, options));
  const [searchTerm, setSearchTerm] = useState<string | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);

  useEffect(() => {
    if (value === previousValue.current) return;
    previousValue.current = value;
    if (value === propagatedValue.current) {
      propagatedValue.current = null;
      return;
    }
    if (value === selectedValue.current) return;
    selectedValue.current = null;
    setQuery(labelForValue(value, options));
    setSearchTerm(null);
    setOpen(false);
    inputRef.current?.setCustomValidity('');
  }, [value, options]);

  useEffect(() => () => {
    requestNumber.current += 1;
    if (blurTimer.current !== null) window.clearTimeout(blurTimer.current);
  }, []);

  function localResults(term: string, browse: boolean): SearchResult[] {
    if (!options) return [];
    const normalized = normalize(term);
    const matches = browse || !normalized
      ? options
      : options.filter((option) => normalize(option.label).includes(normalized));
    return matches.slice(0, MAX_LOCAL_RESULTS);
  }

  async function findResults(term: string, browse: boolean) {
    const current = ++requestNumber.current;
    setActive(-1);
    setOpen(true);
    if (options) {
      setResults(localResults(term, browse));
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
      if (current === requestNumber.current) setResults(items);
    } catch {
      if (current === requestNumber.current) setResults([]);
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
  }

  function choose(result: SearchResult) {
    selectedValue.current = result.id;
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
          setQuery(labelForValue(value, options));
          setSearchTerm(null);
          inputRef.current?.setCustomValidity('');
        }
      }
    }, 0);
  }

  return (
    <div ref={rootRef} className="autocomplete" onBlur={handleBlur}>
      <input
        ref={inputRef} id={id} role="combobox" aria-label={ariaLabel} aria-autocomplete="list" aria-haspopup="listbox"
        aria-expanded={open} aria-controls={listId} aria-busy={loading || undefined}
        aria-activedescendant={open && active >= 0 ? `${listId}-${active}` : undefined}
        value={query} placeholder={placeholder ?? 'Escriba para buscar…'} required={required} disabled={disabled}
        onChange={(event) => {
          const next = event.target.value;
          selectedValue.current = null;
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
            if (!open) { setSearchTerm(null); void findResults('', true); return; }
            if (results.length) setActive((current) => Math.min(current + 1, results.length - 1));
          }
          if (event.key === 'ArrowUp' && open && results.length) {
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
        <ul id={listId} className="autocomplete-results" role="listbox"
          aria-label={ariaLabel ? `Opciones de ${ariaLabel}` : 'Opciones'}>
          {results.length === 0 && !loading
            ? <li className="autocomplete-empty">No se encontraron coincidencias.</li>
            : results.map((result, index) => (
              <li key={result.id} id={`${listId}-${index}`} role="option" aria-selected={active === index}
                  className={active === index ? 'is-active' : ''} onMouseEnter={() => setActive(index)}
                  onMouseDown={(event) => { event.preventDefault(); choose(result); }}>
                {result.label}
              </li>
            ))}
        </ul>
      )}
    </div>
  );
}
