const menuItems = [
  { label: 'Account Settings' },
  { label: 'Notifications' },
  { label: 'Privacy' },
  { label: 'Help & Feedback' },
  { label: 'Sign Out', danger: true },
];

function Profile() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] pb-28">

      <div className="px-5 pt-16 pb-7">
        <p className="text-[11px] font-semibold text-[#444] tracking-widest uppercase mb-2">Ace Vision</p>
        <h1 className="text-3xl font-bold text-white">Profile.</h1>
      </div>

      <div className="px-5 space-y-4">

        {/* Avatar */}
        <div className="card p-6 flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-[#1e1e1e] flex items-center justify-center text-white text-2xl font-black shrink-0">
            A
          </div>
          <div>
            <p className="text-base font-bold text-white">Athlete</p>
            <p className="text-sm text-[#444] mt-0.5">Intermediate · Badminton & Tennis</p>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Sessions', value: '12' },
            { label: 'Avg Score', value: '67' },
            { label: 'Best',      value: '80' },
          ].map(s => (
            <div key={s.label} className="card p-4 text-center">
              <p className="text-2xl font-black text-white tabular-nums">{s.value}</p>
              <p className="text-[10px] text-[#444] mt-1 font-semibold uppercase tracking-wider">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Progress */}
        <div className="card p-4">
          <div className="flex items-center justify-between mb-2">
            <p className="text-xs font-semibold text-[#666]">Season Progress</p>
            <p className="text-xs font-bold text-[#C8FF57] tabular-nums">67 / 100</p>
          </div>
          <div className="h-1 bg-[#1e1e1e] rounded-full overflow-hidden">
            <div className="h-full bg-[#C8FF57] rounded-full" style={{ width: '67%' }} />
          </div>
          <p className="text-[10px] text-[#333] mt-2">33 points to Expert</p>
        </div>

        {/* Menu */}
        <div className="card overflow-hidden divide-y divide-[#1e1e1e]">
          {menuItems.map(item => (
            <button
              key={item.label}
              className={`w-full flex items-center justify-between px-4 py-4 text-sm font-medium transition-colors hover:bg-[#161616] ${
                item.danger ? 'text-red-400' : 'text-[#aaa]'
              }`}
            >
              {item.label}
              {!item.danger && <span className="text-[#333] text-lg">›</span>}
            </button>
          ))}
        </div>

      </div>
    </div>
  );
}

export default Profile;
