import { BrowserRouter, Routes, Route } from 'react-router-dom';
import BottomNav from './components/BottomNav';
import Home    from './pages/Home';
import Record  from './pages/Record';
import Result  from './pages/Result';
import History from './pages/History';
import Drills  from './pages/Drills';
import Profile from './pages/Profile';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"        element={<Home />}    />
        <Route path="/record"  element={<Record />}  />
        <Route path="/result"  element={<Result />}  />
        <Route path="/history" element={<History />} />
        <Route path="/drills"  element={<Drills />}  />
        <Route path="/profile" element={<Profile />} />
      </Routes>
      <BottomNav />
    </BrowserRouter>
  );
}

export default App;
