import { lazy, Suspense } from "react";
import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";

const Home = lazy(() => import("./pages/Home"));
const Photography = lazy(() => import("./pages/Photography"));
const Videos = lazy(() => import("./pages/Videos"));
const Hobbies = lazy(() => import("./pages/Hobbies"));
const Essays = lazy(() => import("./pages/Essays"));
const NotFound = lazy(() => import("./pages/NotFound"));

function PageLoading() {
  return <div className="flex min-h-[60vh] items-center justify-center text-sm text-neutral-500">Loading…</div>;
}

export default function App() {
  return (
    <Suspense fallback={<PageLoading />}>
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
    </Suspense>
  );
}
