import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Splash       from './pages/Splash';
import SignUp       from './pages/SignUp';
import Home        from './pages/Home';
import Result      from './pages/Result';
import MatchResult    from './pages/MatchResult';
import MovementResult from './pages/MovementResult';
import RallyResult    from './pages/RallyResult';
import Advice         from './pages/Advice';

function isTokenValid() {
  if (localStorage.getItem('guest') === 'true') return true;
  const token = localStorage.getItem('token');
  if (!token) return false;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    return payload.exp * 1000 > Date.now();
  } catch {
    return false;
  }
}

function PrivateRoute({ element }) {
  if (!isTokenValid()) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    return <Navigate to="/" replace />;
  }
  return element;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"       element={<Splash />}  />
        <Route path="/signup" element={<SignUp />}  />
        <Route path="/home"         element={<PrivateRoute element={<Home />} />}        />
        <Route path="/result"       element={<PrivateRoute element={<Result />} />}      />
        <Route path="/match-result"    element={<PrivateRoute element={<MatchResult />} />}    />
        <Route path="/movement-result" element={<PrivateRoute element={<MovementResult />} />} />
        <Route path="/rally-result"    element={<PrivateRoute element={<RallyResult />} />}    />
        <Route path="/advice"       element={<PrivateRoute element={<Advice />} />}      />
        <Route path="*"       element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
