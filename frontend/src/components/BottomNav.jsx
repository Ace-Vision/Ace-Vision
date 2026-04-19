import { NavLink } from 'react-router-dom';

const tabs = [
  { to: '/',        icon: '⊞', label: 'Home'    },
  { to: '/history', icon: '◷', label: 'History' },
  { to: '/drills',  icon: '☆',  label: 'Drills'  },
  { to: '/profile', icon: '◯', label: 'Profile' },
];

function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-100 flex z-50">
      {tabs.map(({ to, icon, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `flex-1 flex flex-col items-center py-3 text-xs transition-colors ${
              isActive ? 'text-purple-600' : 'text-gray-400'
            }`
          }
        >
          <span className="text-xl">{icon}</span>
          <span className="mt-1">{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}

export default BottomNav;
