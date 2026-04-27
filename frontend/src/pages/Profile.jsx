function Profile() {
  return (
    <div className="min-h-screen bg-gray-50 pb-24">

      {/* Header */}
      <div className="bg-white px-6 pt-14 pb-4 border-b border-gray-100">
        <h1 className="text-xl font-semibold text-gray-900">Profile</h1>
      </div>

      <div className="px-6 pt-6">

        {/* Avatar */}
        <div className="flex flex-col items-center mb-6">
          <div className="w-20 h-20 rounded-full bg-purple-600 flex items-center justify-center text-white text-3xl font-bold mb-3">
            A
          </div>
          <p className="text-base font-semibold text-gray-900">Athlete</p>
          <p className="text-sm text-gray-400">Intermediate · Badminton & Tennis</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          {[
            { label: 'Sessions', value: '12' },
            { label: 'Avg Score', value: '67' },
            { label: 'Best',      value: '80' },
          ].map(s => (
            <div key={s.label} className="bg-white rounded-xl p-3 text-center border border-gray-100">
              <p className="text-xl font-bold text-purple-700">{s.value}</p>
              <p className="text-xs text-gray-400 mt-1">{s.label}</p>
            </div>
          ))}
        </div>

        {/* Settings rows */}
        <div className="bg-white rounded-xl border border-gray-100 divide-y divide-gray-100">
          {['Account Settings', 'Notifications', 'Privacy', 'Help & Feedback', 'Sign Out'].map(item => (
            <button key={item} className="w-full flex items-center justify-between px-4 py-3.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors">
              {item}
              <span className="text-gray-300">›</span>
            </button>
          ))}
        </div>

      </div>
    </div>
  );
}

export default Profile;
