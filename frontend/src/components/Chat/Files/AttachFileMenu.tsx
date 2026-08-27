import { useState, useRef, useEffect } from 'react';
import { PaperclipIcon, FileTextIcon, SparklesIcon } from '../../Icons';
import './Files.css';

interface AttachFileMenuProps {
  onSelectUpload: () => void;
  disabled?: boolean;
}

export function AttachFileMenu({ onSelectUpload, disabled }: AttachFileMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleUploadClick = () => {
    setIsOpen(false);
    onSelectUpload();
  };

  return (
    <div className="attach-menu-wrapper" ref={menuRef}>
      <button
        type="button"
        className="capsule-icon-btn"
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled}
        title="Adjuntar documento"
      >
        <PaperclipIcon size={17} />
      </button>

      {isOpen && (
        <div className="attach-popover-menu">
          <div className="attach-menu-item" onClick={handleUploadClick}>
            <FileTextIcon size={16} className="attach-menu-item-icon" />
            <span>Subir desde el dispositivo</span>
          </div>
          <div className="attach-menu-item" onClick={handleUploadClick}>
            <span style={{ color: '#059669', display: 'flex' }}>
              <SparklesIcon size={16} className="attach-menu-item-icon" />
            </span>
            <span>Optimizar con MarkItDown</span>
          </div>
          <div className="attach-menu-footer-hint">
            Soporta PDF, DOCX, TXT y XLSX (hasta 25 MB)
          </div>
        </div>
      )}
    </div>
  );
}
