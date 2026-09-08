import { useEffect, useId, useRef, useState } from 'react';
import { searchFormOptions, type SearchResult } from '../../api/formBuilder';

export function SearchAutocompleteField({ source, value, placeholder, disabled, onSelect }: {
  source: string;
  value: string;
  placeholder?: string;
  disabled?: boolean;
  onSelect: (result: SearchResult | null, text: string) => void;
}) {
  const listId = useId();
  const [query, setQuery] = useState(value);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const requestNumber = useRef(0);

  useEffect(() => { setQuery(value); }, [value]);
  useEffect(() => {
    if (query.trim().length < 2 || disabled) { setResults([]); setOpen(false); return; }
    const current = ++requestNumber.current;
    const timer = window.setTimeout(() => {
      setLoading(true);
      searchFormOptions(source, query)
        .then((items) => { if (current === requestNumber.current) { setResults(items); setOpen(true); setActive(-1); } })
        .catch(() => { if (current === requestNumber.current) { setResults([]); setOpen(true); } })
        .finally(() => { if (current === requestNumber.current) setLoading(false); });
    }, 350);
    return () => window.clearTimeout(timer);
  }, [query, source, disabled]);

  function choose(result: SearchResult) {
    setQuery(result.label); setOpen(false); onSelect(result, result.label);
  }

  return (
    <div className="autocomplete">
      <input
        role="combobox" aria-expanded={open} aria-controls={listId}
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        value={query} placeholder={placeholder ?? 'Escriba para buscar…'} disabled={disabled}
        onChange={(event) => { setQuery(event.target.value); onSelect(null, event.target.value); }}
        onBlur={() => window.setTimeout(() => setOpen(false), 120)}
        onFocus={() => { if (results.length || query.length >= 2) setOpen(true); }}
        onKeyDown={(event) => {
          if (!open || !results.length) return;
          if (event.key === 'ArrowDown') { event.preventDefault(); setActive((value) => Math.min(value + 1, results.length - 1)); }
          if (event.key === 'ArrowUp') { event.preventDefault(); setActive((value) => Math.max(value - 1, 0)); }
          if (event.key === 'Enter' && active >= 0) { event.preventDefault(); choose(results[active]); }
          if (event.key === 'Escape') setOpen(false);
        }}
      />
      {loading && <span className="autocomplete-status" role="status">Buscando…</span>}
      {open && (
        <ul id={listId} className="autocomplete-results" role="listbox">
          {results.length === 0 && !loading ? <li className="autocomplete-empty">Sin resultados</li> : results.map((result, index) => (
            <li key={result.id} id={`${listId}-${index}`} role="option" aria-selected={active === index}
                className={active === index ? 'is-active' : ''} onMouseDown={() => choose(result)}>
              {result.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
