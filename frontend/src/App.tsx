import { BrowserRouter, Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import SessionPicker from "./pages/SessionPicker";
import RankingSession from "./pages/RankingSession";
import CollectionView from "./pages/CollectionView";
import Dashboard from "./pages/Dashboard";
import ItemReview from "./pages/ItemReview";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/session/:collectionId" element={<SessionPicker />} />
        <Route path="/rank/:collectionId" element={<RankingSession />} />
        <Route path="/collection/:collectionId" element={<CollectionView />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/review/:collectionId" element={<ItemReview />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
