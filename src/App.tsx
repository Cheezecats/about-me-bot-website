import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Photography from "./pages/Photography";
import Videos from "./pages/Videos";
import Hobbies from "./pages/Hobbies";
import Essays from "./pages/Essays";
import NotFound from "./pages/NotFound";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<Home />} />
        <Route path="photography" element={<Photography />} />
        <Route path="videos" element={<Videos />} />
        <Route path="hobbies" element={<Hobbies />} />
        <Route path="essays" element={<Essays />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
