import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Splash  from './pages/Splash';
import SignUp  from './pages/SignUp';
import Home    from './pages/Home';
import Result  from './pages/Result';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"       element={<Splash />}  />
        <Route path="/signup" element={<SignUp />}  />
        <Route path="/home"   element={<Home />}    />
        <Route path="/result" element={<Result />}  />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
