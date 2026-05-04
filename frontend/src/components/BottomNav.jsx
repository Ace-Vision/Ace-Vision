import { NavLink } from 'react-router-dom';

const tabs = [
  { to: '/',        label: 'Home'    },
  { to: '/history', label: 'History' },
  { to: '/drills',  label: 'Drills'  },
  { to: '/profile', label: 'Profile' },
];

function BottomNav() {
  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-[#0a0a0a] border-t border-[#1e1e1e]">
      <div className="flex">
        {tabs.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              `flex-1 flex items-center justify-center py-4 text-xs font-semibold transition-colors ${
                isActive ? 'text-[#C8FF57]' : 'text-[#444]'
              }`
            }
          >
            {label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

export default BottomNav;
