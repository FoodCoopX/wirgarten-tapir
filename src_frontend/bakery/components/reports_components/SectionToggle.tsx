import React from 'react';
import { ChevronDown, ChevronRight } from 'react-bootstrap-icons';

interface SectionToggleProps {
  isOpen: boolean;
  onToggle: () => void;
  title: string;
  icon: string;
}

export const SectionToggle: React.FC<SectionToggleProps> = ({ isOpen, onToggle, title, icon }) => (
  <h6
    className="d-flex align-items-center mb-2"
    style={{ cursor: 'pointer', userSelect: 'none' }}
    onClick={onToggle}
  >
    {isOpen ? <ChevronDown size={16} className="me-1" /> : <ChevronRight size={16} className="me-1" />}
    <span className="material-icons me-2" style={{ fontSize: '18px' }}>{icon}</span>
    {title}
  </h6>
);