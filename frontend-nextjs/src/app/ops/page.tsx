import type { Metadata } from "next";
import OpsPageClient from "./OpsPageClient";

export const metadata: Metadata = {
  title: "Plum Claims Review Console",
  description: "Internal claims adjudication review for Plum ops team",
};

export default function OpsPage() {
  return <OpsPageClient />;
}
