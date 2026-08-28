import { PaperclipIcon } from '../../Icons';
import './Files.css';

interface AttachFileMenuProps {
  onSelectUpload: () => void;
  disabled?: boolean;
}

export function AttachFileMenu({ onSelectUpload, disabled }: AttachFileMenuProps) {
  return (
    <button
      type="button"
      className="capsule-icon-btn"
      onClick={onSelectUpload}
      disabled={disabled}
      title="Adjuntar documento jurídico (PDF, DOCX, TXT, XLSX)"
    >
      <PaperclipIcon size={17} />
    </button>
  );
}
