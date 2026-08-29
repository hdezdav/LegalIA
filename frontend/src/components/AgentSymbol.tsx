import {
  ScalesIcon,
  ScrollIcon,
  LandmarkIcon,
  ZapIcon,
  BriefcaseIcon,
  BuildingIcon,
  TrendingUpIcon,
  CoinsIcon,
  ShieldIcon,
  BotIcon,
  SparklesIcon,
  FileTextIcon,
} from './Icons';

export interface LegalSymbolDef {
  id: string;
  name: string;
  color: string;
}

export const LEGAL_SYMBOLS: LegalSymbolDef[] = [
  { id: 'scale', name: 'Balanza / General', color: '#2563eb' },
  { id: 'scroll', name: 'Constitucional / Tutela', color: '#d97706' },
  { id: 'landmark', name: 'Civil / CGP', color: '#0284c7' },
  { id: 'zap', name: 'Penal / Ley 906', color: '#ef4444' },
  { id: 'briefcase', name: 'Laboral / CST', color: '#f59e0b' },
  { id: 'building', name: 'Administrativo / CPACA', color: '#3b82f6' },
  { id: 'trending', name: 'Comercial / Minutas', color: '#10b981' },
  { id: 'coins', name: 'Tributario / DIAN', color: '#8b5cf6' },
  { id: 'shield', name: 'Blindaje Legal', color: '#059669' },
  { id: 'bot', name: 'Asistente IA', color: '#6366f1' },
  { id: 'sparkles', name: 'Estrategia', color: '#ec4899' },
  { id: 'file-text', name: 'Auditoría Documental', color: '#64748b' },
];

export function AgentSymbol({
  icon,
  size = 18,
  className = '',
  color,
}: {
  icon?: string;
  size?: number;
  className?: string;
  color?: string;
}) {
  const norm = (icon || 'scale').toLowerCase().trim();

  // Normalize legacy emojis or string IDs
  switch (norm) {
    case 'scroll':
    case 'constitucional':
    case '🏛️':
    case '📜':
      return <ScrollIcon size={size} className={className} style={{ color: color || '#d97706' }} />;
    case 'landmark':
    case 'civil':
    case 'procesal':
    case '🏛':
      return <LandmarkIcon size={size} className={className} style={{ color: color || '#0284c7' }} />;
    case 'zap':
    case 'penal':
    case '⚡':
      return <ZapIcon size={size} className={className} style={{ color: color || '#ef4444' }} />;
    case 'briefcase':
    case 'laboral':
    case '💼':
      return <BriefcaseIcon size={size} className={className} style={{ color: color || '#f59e0b' }} />;
    case 'building':
    case 'administrativo':
    case '🏢':
      return <BuildingIcon size={size} className={className} style={{ color: color || '#3b82f6' }} />;
    case 'trending':
    case 'comercial':
    case 'contratos':
    case '📝':
    case '📈':
      return <TrendingUpIcon size={size} className={className} style={{ color: color || '#10b981' }} />;
    case 'coins':
    case 'tributario':
    case '🪙':
      return <CoinsIcon size={size} className={className} style={{ color: color || '#8b5cf6' }} />;
    case 'shield':
    case '🛡️':
    case '🛡':
      return <ShieldIcon size={size} className={className} style={{ color: color || '#059669' }} />;
    case 'sparkles':
    case '💡':
    case '✨':
      return <SparklesIcon size={size} className={className} style={{ color: color || '#ec4899' }} />;
    case 'file-text':
    case 'doc':
    case '📖':
      return <FileTextIcon size={size} className={className} style={{ color: color || '#64748b' }} />;
    case 'bot':
    case '🤖':
      return <BotIcon size={size} className={className} style={{ color: color || '#6366f1' }} />;
    case 'scale':
    case 'general':
    case '⚖️':
    case '⚖':
    default:
      return <ScalesIcon size={size} className={className} style={{ color: color || '#2563eb' }} />;
  }
}
