import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Splash        from './pages/Splash';
import Home          from './pages/Home';
import Result        from './pages/Result';
import MatchResult    from './pages/MatchResult';
import MovementResult from './pages/MovementResult';
import RallyResult    from './pages/RallyResult';
import Advice         from './pages/Advice';
import MatchHistory   from './pages/MatchHistory';
import Insights       from './pages/Insights';
import OpponentBook   from './pages/OpponentBook';
import OpponentDetail from './pages/OpponentDetail';
import History        from './pages/History';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"                element={<Splash />}        />
        <Route path="/home"            element={<Home />}          />
        <Route path="/result"          element={<Result />}        />
        <Route path="/match-result"    element={<MatchResult />}   />
        <Route path="/movement-result" element={<MovementResult />}/>
        <Route path="/rally-result"    element={<RallyResult />}   />
        <Route path="/advice"          element={<Advice />}        />
        <Route path="/match-history"   element={<MatchHistory />}  />
        <Route path="/insights"        element={<Insights />}      />
        <Route path="/opponent-book"   element={<OpponentBook />}  />
        <Route path="/opponent-detail" element={<OpponentDetail />}/>
        <Route path="/history"         element={<History />}       />
        <Route path="*"                element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
