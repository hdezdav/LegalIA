/**
 * Legal document export utilities for Legalia.
 * Supports exporting drafted legal documents to Word (.doc / .docx), PDF, Markdown, and TXT.
 */

export interface LegalDocMetadata {
  title: string;
  type?: 'contrato' | 'demanda' | 'tutela' | 'peticion' | 'memorial' | 'concepto' | 'otro';
  rawContent: string;
}

/**
 * Clean markdown text to plain formal legal text.
 */
export function cleanMarkdownForLegalDoc(md: string): string {
  return md
    .replace(/^#+\s+/gm, '') // Remove markdown headers
    .replace(/\*\*(.*?)\*\*/g, '$1') // Remove bold
    .replace(/\*(.*?)\*/g, '$1') // Remove italic
    .replace(/\[\^?\d+\]/g, '') // Remove citation numbers
    .replace(/`{1,3}[^`]*`{1,3}/g, '') // Remove code blocks
    .trim();
}

/**
 * Format markdown to HTML styled specifically for Colombian legal documents.
 */
export function markdownToLegalHtml(title: string, markdown: string): string {
  // Convert basic markdown elements to legal-styled HTML
  const lines = markdown.split('\n');
  const htmlParts: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line) {
      i++;
      continue;
    }

    // Detección y parseo de tablas en Markdown
    if (line.startsWith('|') && line.endsWith('|') && i + 1 < lines.length && lines[i + 1].includes('|') && lines[i + 1].includes('---')) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('|') && lines[i].trim().endsWith('|')) {
        tableLines.push(lines[i].trim());
        i++;
      }

      let tableHtml = '<table class="legal-table">\n<thead>\n<tr>';
      const rows = tableLines.filter((tl) => !/^\|(\s*:?-+:?\s*\|)+$/.test(tl));
      if (rows.length > 0) {
        const headerCells = rows[0].slice(1, -1).split('|').map((c) => c.trim());
        headerCells.forEach((hc) => {
          tableHtml += `<th>${hc}</th>`;
        });
        tableHtml += '</tr>\n</thead>\n<tbody>';

        for (let r = 1; r < rows.length; r++) {
          tableHtml += '\n<tr>';
          const cells = rows[r].slice(1, -1).split('|').map((c) => c.trim());
          cells.forEach((cell) => {
            const formatted = cell
              .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
              .replace(/\*(.*?)\*/g, '<em>$1</em>');
            tableHtml += `<td>${formatted}</td>`;
          });
          tableHtml += '</tr>';
        }
        tableHtml += '\n</tbody>\n</table>';
        htmlParts.push(tableHtml);
      }
      continue;
    }

    if (line.startsWith('### ')) {
      htmlParts.push(`<h3>${line.replace('### ', '')}</h3>`);
    } else if (line.startsWith('## ')) {
      htmlParts.push(`<h2>${line.replace('## ', '')}</h2>`);
    } else if (line.startsWith('# ')) {
      htmlParts.push(`<h1>${line.replace('# ', '')}</h1>`);
    } else if (line.startsWith('**') && line.endsWith('**')) {
      htmlParts.push(`<p class="clause-header"><strong>${line.replace(/\*\*/g, '')}</strong></p>`);
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      htmlParts.push(`<li>${line.substring(2)}</li>`);
    } else if (/^\d+\.\s+/.test(line)) {
      htmlParts.push(`<li>${line.replace(/^\d+\.\s+/, '')}</li>`);
    } else if (line === '---' || line === '***') {
      htmlParts.push('<hr class="legal-divider" />');
    } else {
      // Paragraph with bold/italic replacements
      let formatted = line
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>');
      htmlParts.push(`<p>${formatted}</p>`);
    }
    i++;
  }

  return `
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>${title}</title>
  <style>
    @page {
      size: letter;
      margin: 2.54cm 2.54cm 2.54cm 2.54cm;
    }
    body {
      font-family: 'Times New Roman', Times, serif, 'Segoe UI', Arial;
      font-size: 12pt;
      line-height: 1.5;
      color: #111827;
      margin: 0;
      padding: 2.5cm;
      background: #ffffff;
      text-align: justify;
    }
    h1 {
      font-size: 14pt;
      font-weight: bold;
      text-align: center;
      text-transform: uppercase;
      margin-bottom: 20pt;
      border-bottom: 2px solid #1e3a8a;
      padding-bottom: 8pt;
      color: #0f172a;
    }
    h2 {
      font-size: 12.5pt;
      font-weight: bold;
      margin-top: 16pt;
      margin-bottom: 8pt;
      color: #1e3a8a;
      text-transform: uppercase;
    }
    h3 {
      font-size: 11.5pt;
      font-weight: bold;
      margin-top: 12pt;
      margin-bottom: 6pt;
    }
    p {
      margin-top: 0;
      margin-bottom: 10pt;
      text-indent: 1.25cm;
    }
    .clause-header {
      font-weight: bold;
      text-indent: 0;
      margin-top: 14pt;
      margin-bottom: 4pt;
      color: #0f172a;
    }
    ul, ol {
      margin-top: 4pt;
      margin-bottom: 10pt;
      padding-left: 2cm;
    }
    li {
      margin-bottom: 4pt;
    }
    .legal-divider {
      border: 0;
      border-top: 1px solid #94a3b8;
      margin: 20pt 0;
    }
    .legal-table {
      width: 100%;
      border-collapse: collapse;
      margin: 14pt 0;
      font-size: 10.5pt;
      page-break-inside: avoid;
    }
    .legal-table th, .legal-table td {
      border: 1px solid #94a3b8;
      padding: 6pt 8pt;
      text-align: left;
    }
    .legal-table th {
      background-color: #f1f5f9;
      font-weight: bold;
      color: #0f172a;
    }
    .signature-section {
      margin-top: 40pt;
      display: flex;
      justify-content: space-between;
      page-break-inside: avoid;
    }
    .signature-box {
      width: 45%;
      border-top: 1px solid #000;
      padding-top: 6pt;
      text-align: center;
      font-size: 11pt;
    }
    @media print {
      body {
        padding: 0;
      }
      .no-print {
        display: none;
      }
    }
  </style>
</head>
<body>
  <h1>${title}</h1>
  ${htmlParts.join('\n  ')}
</body>
</html>
`;
}

/**
 * Export document as real native Word (.docx) with official legal formatting.
 */
export async function exportToWord(title: string, content: string): Promise<void> {
  const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'documento_legalia';

  try {
    const response = await fetch('/api/v1/tools/export-docx', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title, content }),
    });

    if (response.ok) {
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${slug}.docx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      return;
    }
  } catch (err) {
    console.warn('Backend docx export failed, falling back to local export', err);
  }

  // Fallback if backend is unreachable
  exportToMarkdown(title, content);
}

/**
 * Print / Save as PDF via native printable dialog.
 */
export function exportToPdf(title: string, content: string): void {
  const html = markdownToLegalHtml(title, content);
  const printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
      printWindow.print();
    }, 400);
  }
}

/**
 * Export raw Markdown / TXT.
 */
export function exportToMarkdown(title: string, content: string): void {
  const slug = title.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '') || 'documento_legalia';
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${slug}.md`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
