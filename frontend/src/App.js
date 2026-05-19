import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Splash  from './pages/Splash';
import SignUp  from './pages/SignUp';
import Home    from './pages/Home';
import Result  from './pages/Result';
import Advice  from './pages/Advice';

function PrivateRoute({ element }) {
  const token = localStorage.getItem('token');
  return token ? element : <Navigate to="/" replace />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"       element={<Splash />}  />
        <Route path="/signup" element={<SignUp />}  />
        <Route path="/home"   element={<PrivateRoute element={<Home />} />}    />
        <Route path="/result" element={<PrivateRoute element={<Result />} />}  />
        <Route path="/advice" element={<PrivateRoute element={<Advice />} />}  />
        <Route path="*"       element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
