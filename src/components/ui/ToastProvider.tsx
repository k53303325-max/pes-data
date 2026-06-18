"use client";

import { Toaster } from "sonner";

export function ToastProvider() {
  return (
    <Toaster
      theme="dark"
      position="top-right"
      toastOptions={{
        style: {
          background: "#1E1E3A",
          border: "1px solid rgba(91, 95, 199, 0.3)",
          color: "#F4F4FC",
        },
      }}
    />
  );
}
