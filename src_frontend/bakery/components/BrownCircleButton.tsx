import React from 'react';

interface BrownCircleButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
  children: React.ReactNode;
}

export const BrownCircleButton: React.FC<BrownCircleButtonProps> = ({
  active = false,
  children,
  style,
  ...props
}) => (
  <button
    className="btn btn-sm rounded-circle"
    style={{
      width: '32px',
      height: '32px',
      backgroundColor: active ? '#D4A574' : '#8B4513',
      color: active ? 'white' : 'white',
      ...style,
    }}
    {...props}
  >
    {children}
  </button>
);