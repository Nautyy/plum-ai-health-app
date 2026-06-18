"use client";

import { useEffect, useState } from "react";
import type { DemoTestCase } from "@/types/claim";
import { fetchTestCases } from "@/data/demoTestCases";
import ChatApp from "@/components/chat/ChatApp";

export default function OpsPageClient() {
  const [demoCases, setDemoCases] = useState<DemoTestCase[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    fetchTestCases()
      .then(setDemoCases)
      .catch((err) => {
        setLoadError(err instanceof Error ? err.message : "Could not load test scenarios");
      });
  }, []);

  return (
    <>
      {loadError && (
        <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-center text-sm text-amber-900">
          Test scenarios unavailable: {loadError}
        </div>
      )}
      <ChatApp audience="ops" demoCases={demoCases} />
    </>
  );
}
