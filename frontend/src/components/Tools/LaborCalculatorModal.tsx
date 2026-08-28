import { useState, FormEvent } from 'react';
import { exportToWord } from '../../utils/documentExport';
import { SparklesIcon, DownloadIcon } from '../Icons';
import './LaborCalculatorModal.css';

interface LaborSettlementResult {
  dias_laborados_totales: number;
  salario_base_liquidacion: number;
  auxilio_transporte_monto: number;
  base_prestacional: number;
  cesantias: number;
  intereses_cesantias: number;
  prima_servicios: number;
  vacaciones_compensadas: number;
  indemnizacion_despido: number;
  total_liquidacion: number;
  desglose_normativo: Record<string, string>;
}

interface LaborCalculatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onInsertToChat?: (text: string) => void;
}

export function LaborCalculatorModal({
  isOpen,
  onClose,
  onInsertToChat,
}: LaborCalculatorModalProps) {
  const [fechaInicio, setFechaInicio] = useState('2024-01-15');
  const [fechaFin, setFechaFin] = useState('2026-08-28');
  const [salarioBase, setSalarioBase] = useState('3500000');
  const [motivoTerminacion, setMotivoTerminacion] = useState('despido_sin_justa_causa');
  const [tipoContrato, setTipoContrato] = useState('indefinido');
  const [auxilioTransporte, setAuxilioTransporte] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<LaborSettlementResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleCalculate = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const resp = await fetch('/api/v1/tools/calculate-labor-settlement', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fecha_inicio: fechaInicio,
          fecha_fin: fechaFin,
          salario_base: parseFloat(salarioBase) || 0,
          motivo_terminacion: motivoTerminacion,
          tipo_contrato: tipoContrato,
          auxilio_transporte: auxilioTransporte,
        }),
      });

      if (!resp.ok) {
        throw new Error('Error al procesar la liquidación laboral');
      }

      const data = await resp.json();
      setResult(data);
    } catch (err: any) {
      setError(err.message || 'Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const formatCOP = (val: number) => {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      maximumFractionDigits: 0,
    }).format(val);
  };

  const buildSummaryMarkdown = () => {
    if (!result) return '';
    return `### LIQUIDACIÓN OFICIAL DE PRESTACIONES E INDEMNIZACIONES (CST)
- **Periodo Laborado**: ${fechaInicio} a ${fechaFin} (${result.dias_laborados_totales} días)
- **Salario Base**: ${formatCOP(result.salario_base_liquidacion)}
- **Auxilio de Transporte**: ${formatCOP(result.auxilio_transporte_monto)}
- **Base Prestacional**: ${formatCOP(result.base_prestacional)}
- **Motivo de Terminación**: ${motivoTerminacion.replace(/_/g, ' ')}
- **Tipo de Contrato**: ${tipoContrato.replace(/_/g, ' ')}

#### Desglose de Conceptos:
1. **Cesantías (Art. 249 CST)**: ${formatCOP(result.cesantias)}
2. **Intereses sobre Cesantías (Ley 52/1975)**: ${formatCOP(result.intereses_cesantias)}
3. **Prima de Servicios (Art. 306 CST)**: ${formatCOP(result.prima_servicios)}
4. **Vacaciones Compensadas (Art. 186 CST)**: ${formatCOP(result.vacaciones_compensadas)}
5. **Indemnización por Despido (Art. 64 CST)**: ${formatCOP(result.indemnizacion_despido)}

**TOTAL LIQUIDACIÓN**: **${formatCOP(result.total_liquidacion)}**`;
  };

  const handleSendToChat = () => {
    if (!result || !onInsertToChat) return;
    const text = buildSummaryMarkdown();
    onInsertToChat(
      `Por favor analiza la siguiente liquidación laboral y elabora el memorial de reclamación formal o finiquito:\n\n${text}`
    );
    onClose();
  };

  const handleExportDocx = () => {
    if (!result) return;
    const text = buildSummaryMarkdown();
    exportToWord('LIQUIDACION_LABORAL_OFICIAL', text);
  };

  return (
    <div className="labor-modal-overlay" onClick={onClose}>
      <div className="labor-modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="labor-modal-header">
          <div className="labor-modal-title-group">
            <span className="labor-modal-badge">Herramienta Jurídica</span>
            <h3 className="labor-modal-title">Calculadora de Liquidación Laboral (CST)</h3>
          </div>
          <button type="button" className="labor-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="labor-modal-body">
          <form onSubmit={handleCalculate} className="labor-form-grid">
            <div className="labor-field">
              <label>Fecha de Inicio de Labores</label>
              <input
                type="date"
                value={fechaInicio}
                onChange={(e) => setFechaInicio(e.target.value)}
                required
              />
            </div>

            <div className="labor-field">
              <label>Fecha de Terminación</label>
              <input
                type="date"
                value={fechaFin}
                onChange={(e) => setFechaFin(e.target.value)}
                required
              />
            </div>

            <div className="labor-field">
              <label>Salario Mensual Base (COP)</label>
              <input
                type="number"
                min="0"
                step="10000"
                value={salarioBase}
                onChange={(e) => setSalarioBase(e.target.value)}
                required
              />
            </div>

            <div className="labor-field">
              <label>Motivo de Terminación</label>
              <select
                value={motivoTerminacion}
                onChange={(e) => setMotivoTerminacion(e.target.value)}
              >
                <option value="despido_sin_justa_causa">Despido Sin Justa Causa (con indemnización)</option>
                <option value="despido_con_justa_causa">Despido Con Justa Causa</option>
                <option value="renuncia">Renuncia Voluntaria</option>
                <option value="mutuo_acuerdo">Mutuo Acuerdo / Transacción</option>
              </select>
            </div>

            <div className="labor-field">
              <label>Tipo de Contrato</label>
              <select
                value={tipoContrato}
                onChange={(e) => setTipoContrato(e.target.value)}
              >
                <option value="indefinido">Término Indefinido</option>
                <option value="termino_fijo">Término Fijo</option>
                <option value="obra_labor">Por Obra o Labor Determinada</option>
              </select>
            </div>

            <div className="labor-field labor-checkbox-field">
              <label className="checkbox-container">
                <input
                  type="checkbox"
                  checked={auxilioTransporte}
                  onChange={(e) => setAuxilioTransporte(e.target.checked)}
                />
                <span>Incluir Auxilio de Transporte si devenga hasta 2 SMMLV</span>
              </label>
            </div>

            <div className="labor-submit-row">
              <button type="submit" className="labor-calc-btn" disabled={loading}>
                <SparklesIcon size={15} />
                <span>{loading ? 'Calculando...' : 'Calcular Liquidación Oficial'}</span>
              </button>
            </div>
          </form>

          {error && <div className="labor-error-msg">{error}</div>}

          {result && (
            <div className="labor-results-card">
              <div className="results-header">
                <h4>Resumen Liquidatorio · {result.dias_laborados_totales} Días Laborados</h4>
              </div>

              <div className="results-table-wrap">
                <table className="results-table">
                  <tbody>
                    <tr>
                      <td>Cesantías (Art. 249 CST)</td>
                      <td className="amount">{formatCOP(result.cesantias)}</td>
                    </tr>
                    <tr>
                      <td>Intereses s/ Cesantías (Ley 52/1975)</td>
                      <td className="amount">{formatCOP(result.intereses_cesantias)}</td>
                    </tr>
                    <tr>
                      <td>Prima de Servicios (Art. 306 CST)</td>
                      <td className="amount">{formatCOP(result.prima_servicios)}</td>
                    </tr>
                    <tr>
                      <td>Vacaciones Compensadas (Art. 186 CST)</td>
                      <td className="amount">{formatCOP(result.vacaciones_compensadas)}</td>
                    </tr>
                    {result.indemnizacion_despido > 0 && (
                      <tr className="row-indem">
                        <td>Indemnización Despido (Art. 64 CST)</td>
                        <td className="amount">{formatCOP(result.indemnizacion_despido)}</td>
                      </tr>
                    )}
                    <tr className="row-total">
                      <td>TOTAL A LIQUIDAR</td>
                      <td className="amount-total">{formatCOP(result.total_liquidacion)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div className="results-actions">
                <button
                  type="button"
                  className="results-btn-primary"
                  onClick={handleSendToChat}
                >
                  <SparklesIcon size={14} />
                  <span>Insertar en Legalia para redactar minuta</span>
                </button>
                <button
                  type="button"
                  className="results-btn-secondary"
                  onClick={handleExportDocx}
                >
                  <DownloadIcon size={14} />
                  <span>Descargar Word (.docx)</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
