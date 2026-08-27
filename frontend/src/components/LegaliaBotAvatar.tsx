import React, { useEffect, useState } from 'react';
import { createAvatar } from '@bible-strong/avatar-react';
import '@bible-strong/avatar-react/styles.css';
import avatarJson from '../assets/legalia.avatar.json';
import './LegaliaBotAvatar.css';

const InternalAvatar = createAvatar(avatarJson as any);

export type BotAvatarState = 'idle' | 'thinking' | 'answering' | 'happy';

export interface LegaliaBotAvatarProps {
  state?: BotAvatarState;
  size?: number | string;
  className?: string;
  interactive?: boolean;
  glow?: boolean;
  onClick?: () => void;
}

/** How long a click-triggered 'happy' animation plays before reverting. */
const HAPPY_DURATION_MS = 2500;

export const LegaliaBotAvatar: React.FC<LegaliaBotAvatarProps> = ({
  state = 'idle',
  size = 32,
  className = '',
  interactive = false,
  glow = false,
  onClick,
}) => {
  // Driven through the library's *controlled* `animation` prop. The previous
  // version passed `defaultAnimation`, which the library only reads once on
  // mount, so the avatar never actually changed animation when `state` changed —
  // and it additionally called controller.play(), which the library rejects as
  // `controlled_by_props` when mixed with prop-driven animation.
  const [celebrating, setCelebrating] = useState(false);

  const activeAnimation: BotAvatarState = celebrating ? 'happy' : state;

  useEffect(() => {
    if (!celebrating) return;
    const timeout = setTimeout(() => setCelebrating(false), HAPPY_DURATION_MS);
    return () => clearTimeout(timeout);
  }, [celebrating]);

  // A new incoming state (e.g. the model started answering) outranks an
  // in-flight click celebration.
  useEffect(() => {
    setCelebrating(false);
  }, [state]);

  const handleClick = () => {
    if (interactive) setCelebrating(true);
    onClick?.();
  };

  const parsedSize = typeof size === 'number' ? `${size}px` : size;

  return (
    <div
      className={`legalia-bot-avatar-wrapper state-${activeAnimation} ${
        interactive ? 'interactive' : ''
      } ${glow ? 'has-glow' : ''} ${className}`}
      style={{ width: parsedSize, height: parsedSize }}
      onClick={handleClick}
      role={interactive ? 'button' : undefined}
      tabIndex={interactive ? 0 : undefined}
      title={interactive ? 'Haz clic para interactuar con Legalia' : undefined}
    >
      <div className="avatar-ambient-glow" />
      <InternalAvatar
        animation={activeAnimation}
        size={size}
        className="legalia-bot-avatar-inner"
        ariaLabel="Legalia"
        onError={(error) => {
          // Surface a bad animation key instead of failing silently.
          console.warn('[LegaliaBotAvatar] animation error', error);
        }}
      />
    </div>
  );
};
