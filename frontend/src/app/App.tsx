import { lazy, Suspense } from "react";
import { createBrowserRouter, Link, Outlet, RouterProvider } from "react-router-dom";
import { Toaster } from "@/components/ui";
import { useGlobalSync } from "./realtime";

const Home = lazy(() => import("@/pages/Home"));
const Stage = lazy(() => import("@/pages/Stage"));
const MerchantPhone = lazy(() => import("@/pages/MerchantPhone"));
const Soundbox = lazy(() => import("@/pages/Soundbox"));
const Console = lazy(() => import("@/pages/Console"));
const Inject = lazy(() => import("@/pages/Inject"));
const Travel = lazy(() => import("@/pages/Travel"));
const Eval = lazy(() => import("@/pages/Eval"));

import { useStore } from "@/store";
import { useEffect } from "react";

function Shell() {
  useGlobalSync();
  const theme = useStore((s) => s.theme);
  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [theme]);

  return (
    <>
      <Suspense fallback={<div className="grid h-full place-items-center text-muted">Loading…</div>}>
        <Outlet />
      </Suspense>
      <Toaster />
    </>
  );
}

function NotFound() {
  return (
    <div className="grid h-full place-items-center p-6 text-center">
      <div>
        <h1 className="text-xl font-bold">Page not found</h1>
        <Link to="/" className="text-sky-700 underline">Go home</Link>
      </div>
    </div>
  );
}

const router = createBrowserRouter([
  {
    element: <Shell />,
    children: [
      { path: "/", element: <Home /> },
      { path: "/stage", element: <Stage /> },
      { path: "/merchant", element: <MerchantPhone /> },
      { path: "/soundbox", element: <Soundbox /> },
      { path: "/console", element: <Console /> },
      { path: "/inject", element: <Inject /> },
      { path: "/travel", element: <Travel /> },
      { path: "/eval", element: <Eval /> },
      { path: "*", element: <NotFound /> },
    ],
  },
]);

export default function App() {
  return <RouterProvider router={router} />;
}
