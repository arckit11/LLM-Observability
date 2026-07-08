'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function Sidebar() {
  const pathname = usePathname();

  const links = [
    { name: 'Overview', href: '/', icon: '📊' },
    { name: 'Traces', href: '/traces', icon: '🔍' },
    { name: 'Cost Analytics', href: '/cost', icon: '💰' },
    { name: 'Latency Metrics', href: '/latency', icon: '⚡' },
    { name: 'Alerts', href: '/alerts', icon: '🔔' },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">🌌</div>
          <div className="sidebar-logo-text">LLM Observatory</div>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="sidebar-section-label">Observability</div>
        {links.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`sidebar-link ${isActive ? 'active' : ''}`}
            >
              <span className="sidebar-link-icon">{link.icon}</span>
              {link.name}
            </Link>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="sidebar-version">
          <span className="sidebar-version-dot"></span>
          v0.1.0 (Active)
        </div>
      </div>
    </aside>
  );
}
