import { useMemo } from 'react';
import { CitationItem } from '../../types';
import { GlobeIcon, ExternalLinkIcon, FileTextIcon } from '../Icons';
import './SourcesRail.css';

export interface SourceItem {
  id: string;
  title: string;
  url: string;
  domain: string;
  snippet?: string;
  type: 'web' | 'court' | 'statute';
}

function getDomain(urlStr: string): string {
  try {
    const url = new URL(urlStr);
    return url.hostname.replace(/^www\./, '');
  } catch {
    return 'jurisprudencia.gov.co';
  }
}

export function extractSources(
  markdown: string,
  metadataCitations?: CitationItem[] | Array<{ title?: string; url?: string; snippet?: string }>
): SourceItem[] {
  const sourcesMap = new Map<string, SourceItem>();

  // 1. Ingest metadata citations if available from RAG
  if (metadataCitations && Array.isArray(metadataCitations)) {
    metadataCitations.forEach((c: any, idx) => {
      const title = c.documentTitle
        ? `${c.documentTitle} ${c.sectionLabel ? `(${c.sectionLabel})` : ''}`.trim()
        : (c.title || `Fuente ${idx + 1}`);
      const url = c.url || (title ? `https://www.corteconstitucional.gov.co/relatoria/buscador_relatoria.php?q=${encodeURIComponent(title)}` : '');
      const domain = c.url ? getDomain(c.url) : 'jurisprudencia.gov.co';
      const snippet = c.snippetText || c.snippet || '';

      sourcesMap.set(title.toLowerCase(), {
        id: `meta-${idx}`,
        title,
        url,
        domain,
        snippet,
        type: domain.includes('corte') || domain.includes('rama') ? 'court' : 'web',
      });
    });
  }

  if (!markdown) return Array.from(sourcesMap.values());

  // 2. Extract standard markdown links: [Title](https://...)
  const mdLinkRegex = /\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g;
  let match: RegExpExecArray | null;
  let linkIdx = 0;

  while ((match = mdLinkRegex.exec(markdown)) !== null) {
    const title = match[1].trim();
    const url = match[2].trim();
    const domain = getDomain(url);
    const key = url.toLowerCase();

    // Exclude self-references or purely internal anchor links
    if (url.startsWith('http') && !sourcesMap.has(key)) {
      sourcesMap.set(key, {
        id: `link-${linkIdx++}`,
        title: title.length > 5 ? title : domain,
        url,
        domain,
        type: domain.includes('corte') || domain.includes('suin') || domain.includes('ramajudicial') ? 'court' : 'web',
      });
    }
  }

  // 3. Extract raw URLs if not already matched
  const rawUrlRegex = /(https?:\/\/[^\s\)\],<]+)/g;
  while ((match = rawUrlRegex.exec(markdown)) !== null) {
    const url = match[1].trim();
    const key = url.toLowerCase();
    if (!sourcesMap.has(key)) {
      const domain = getDomain(url);
      sourcesMap.set(key, {
        id: `raw-${linkIdx++}`,
        title: domain,
        url,
        domain,
        type: 'web',
      });
    }
  }

  // 4. Extract Colombian Court Precedents (Sentencias) if no web links were explicitly given
  if (sourcesMap.size === 0) {
    const sentenceRegex = /\b(Sentencia\s+(?:C|SU|T|SL|SC|SP|STC|STL)-[0-9]{2,4}\s*(?:\/|\s*de\s*)[0-9]{2,4})\b/gi;
    const foundSentences = new Set<string>();
    while ((match = sentenceRegex.exec(markdown)) !== null) {
      foundSentences.add(match[1].trim());
    }

    Array.from(foundSentences).slice(0, 4).forEach((sent, idx) => {
      const searchUrl = `https://www.corteconstitucional.gov.co/relatoria/buscador_relatoria.php?q=${encodeURIComponent(sent)}`;
      sourcesMap.set(sent.toLowerCase(), {
        id: `sent-${idx}`,
        title: sent,
        url: searchUrl,
        domain: 'corteconstitucional.gov.co',
        type: 'court',
      });
    });
  }

  return Array.from(sourcesMap.values()).slice(0, 6);
}

interface SourcesRailProps {
  markdown: string;
  metadataCitations?: CitationItem[] | Array<{ title?: string; url?: string; snippet?: string }>;
}

export function SourcesRail({ markdown, metadataCitations }: SourcesRailProps) {
  const sources = useMemo(
    () => extractSources(markdown, metadataCitations),
    [markdown, metadataCitations]
  );

  if (sources.length === 0) return null;

  return (
    <div className="perplexity-sources-section">
      <div className="sources-rail-header">
        <GlobeIcon size={14} className="sources-globe-icon" />
        <span className="sources-rail-title">Fuentes y Referencias ({sources.length})</span>
      </div>

      <div className="sources-cards-grid">
        {sources.map((source, index) => {
          const faviconUrl = `https://www.google.com/s2/favicons?domain=${source.domain}&sz=32`;

          return (
            <a
              key={source.id || index}
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="perplexity-source-card"
              title={`Abrir fuente: ${source.title} (${source.domain})`}
            >
              <div className="source-card-header">
                <div className="source-favicon-wrapper">
                  <img
                    src={faviconUrl}
                    alt=""
                    className="source-favicon"
                    onError={(e) => {
                      (e.target as HTMLElement).style.display = 'none';
                    }}
                  />
                  <FileTextIcon size={12} className="source-fallback-icon" />
                </div>
                <span className="source-card-domain">{source.domain}</span>
                <span className="source-card-num">[{index + 1}]</span>
              </div>

              <div className="source-card-body">
                <span className="source-card-title">{source.title}</span>
              </div>

              <div className="source-card-footer">
                <span className="source-visit-label">Consultar fuente</span>
                <ExternalLinkIcon size={11} className="source-ext-icon" />
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
}
