"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

/** While a note is being read, the page asks again every few seconds, so she never has to reload it. */
export function Rereads({ every = 5000 }: { every?: number }) {
  const router = useRouter();
  useEffect(() => {
    const t = setInterval(() => router.refresh(), every);
    return () => clearInterval(t);
  }, [router, every]);
  return null;
}
