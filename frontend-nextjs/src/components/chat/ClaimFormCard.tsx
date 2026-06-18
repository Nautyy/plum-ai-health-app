"use client";

import { useEffect, useMemo, useState } from "react";
import type { ClaimSubmissionPayload } from "@/types/claim";
import {
  type ClaimFor,
  claimForOptionsForEmployee,
  familyForEmployee,
  lookupEmployee,
  resolvePolicyMember,
} from "@/data/policyMembers";

type DocumentEntry = {
  file_id: string;
  file_name: string;
  actual_type: string;
  mime_type: string;
  file_content_base64: string;
  content_summary: string;
  content_source?: string;
  patient_name_on_doc?: string;
};

type Props = {
  loading: boolean;
  variant?: "member" | "ops";
  onSubmit: (payload: ClaimSubmissionPayload) => Promise<void>;
};

const CATEGORIES = [
  "CONSULTATION",
  "DIAGNOSTIC",
  "PHARMACY",
  "DENTAL",
  "VISION",
  "ALTERNATIVE_MEDICINE",
];

const DOC_TYPES = [
  "PRESCRIPTION",
  "HOSPITAL_BILL",
  "PHARMACY_BILL",
  "LAB_REPORT",
  "DIAGNOSTIC_REPORT",
];

function guessDocType(mimeType: string): string {
  if (mimeType.startsWith("text/")) {
    return "PRESCRIPTION";
  }
  return "";
}

export default function ClaimFormCard({ loading, variant = "member", onSubmit }: Props) {
  const [memberId, setMemberId] = useState("");
  const [claimFor, setClaimFor] = useState<ClaimFor>("SELF");
  const [patientName, setPatientName] = useState("");
  const [category, setCategory] = useState("CONSULTATION");
  const [treatmentDate, setTreatmentDate] = useState("");
  const [claimedAmount, setClaimedAmount] = useState("");
  const [hospitalName, setHospitalName] = useState("");
  const [documents, setDocuments] = useState<DocumentEntry[]>([]);
  const [textDoc, setTextDoc] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const policyMember = useMemo(() => resolvePolicyMember(memberId), [memberId]);
  const employee = useMemo(() => lookupEmployee(memberId), [memberId]);
  const claimForOptions = useMemo(
    () => claimForOptionsForEmployee(memberId),
    [memberId]
  );
  const beneficiary = useMemo(
    () => familyForEmployee(memberId, claimFor),
    [memberId, claimFor]
  );

  useEffect(() => {
    if (claimForOptions.length === 0) {
      setPatientName("");
      return;
    }
    if (!claimForOptions.some((o) => o.value === claimFor)) {
      setClaimFor(claimForOptions[0].value);
      return;
    }
    const selected = claimForOptions.find((o) => o.value === claimFor);
    if (selected) setPatientName(selected.memberName);
  }, [claimFor, claimForOptions]);

  const addFile = async (file: File) => {
    const buffer = await file.arrayBuffer();
    const base64 = btoa(String.fromCharCode(...new Uint8Array(buffer)));
    setDocuments((prev) => [
      ...prev,
      {
        file_id: `F${prev.length + 1}`,
        file_name: file.name,
        actual_type: guessDocType(file.type || ""),
        mime_type: file.type || "application/octet-stream",
        file_content_base64: base64,
        content_summary: "",
      },
    ]);
  };

  const removeDocument = (fileId: string) => {
    setDocuments((prev) => prev.filter((doc) => doc.file_id !== fileId));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    const docs = [...documents];
    if (textDoc.trim()) {
      docs.push({
        file_id: `F${docs.length + 1}`,
        file_name: "prescription.txt",
        actual_type: "PRESCRIPTION",
        mime_type: "text/plain",
        file_content_base64: "",
        content_summary: textDoc,
        content_source: "user_paste",
      });
    }

    if (docs.length === 0) {
      setFormError("Upload at least one document.");
      return;
    }

    const untyped = docs.filter((d) => !d.actual_type);
    if (untyped.length > 0) {
      setFormError(`Select document type for: ${untyped.map((d) => d.file_name).join(", ")}`);
      return;
    }

    const parsedAmount = Number(claimedAmount.replace(/,/g, ""));
    if (!claimedAmount.trim() || !Number.isFinite(parsedAmount) || parsedAmount <= 0) {
      setFormError("Enter a valid claimed amount greater than zero.");
      return;
    }

    const employeeId = memberId.trim().toUpperCase();
    if (!resolvePolicyMember(employeeId)) {
      setFormError("Employee ID not found on policy. Use your Plum employee ID (e.g. EMP001).");
      return;
    }

    if (!claimForOptions.some((o) => o.value === claimFor)) {
      setFormError("Select who this claim is for.");
      return;
    }

    const patientHint = patientName.trim() || beneficiary?.name || "";
    const docsWithPatient = docs.map((doc) =>
      patientHint && !doc.content_summary
        ? { ...doc, patient_name_on_doc: patientHint }
        : doc
    );

    onSubmit({
      member_id: employeeId,
      policy_id: "PLUM_GHI_2024",
      claim_category: category,
      treatment_date: treatmentDate,
      claimed_amount: parsedAmount,
      claim_for: claimFor,
      patient_name: patientHint || undefined,
      hospital_name: hospitalName || undefined,
      documents: docsWithPatient.map(({ file_content_base64, content_summary, actual_type, patient_name_on_doc, ...rest }) => ({
        ...rest,
        actual_type,
        file_content_base64: file_content_base64 || undefined,
        content_summary: content_summary || undefined,
        patient_name_on_doc: patient_name_on_doc || undefined,
      })),
    });
  };

  const inputClass =
    "mt-1 w-full rounded-xl border border-border bg-white px-3 py-2.5 text-sm text-text outline-none transition focus:border-plum-brand/50 focus:ring-2 focus:ring-plum-brand/10";

  return (
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl border border-border bg-white p-5 shadow-sm ring-1 ring-black/[0.03]"
    >
      <p className="mb-4 text-sm font-semibold text-text">
        {variant === "ops" ? "Claim input for adjudication" : "Submit your claim details"}
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-xs font-medium text-text-muted">Employee ID</span>
          <input
            className={inputClass}
            value={memberId}
            onChange={(e) => setMemberId(e.target.value.toUpperCase())}
            placeholder="EMP001"
            required
          />
          {policyMember && (
            <p className="mt-1 text-xs text-text-muted">
              {policyMember.primary_member_id ? (
                <>
                  Enrolled member:{" "}
                  <span className="font-medium text-text">{policyMember.name}</span>
                  {employee && (
                    <>
                      {" "}
                      · Policy holder:{" "}
                      <span className="font-medium text-text">{employee.name}</span>
                    </>
                  )}
                </>
              ) : (
                <>
                  Policy holder:{" "}
                  <span className="font-medium text-text">{policyMember.name}</span>
                </>
              )}
            </p>
          )}
        </label>

        <label className="block">
          <span className="text-xs font-medium text-text-muted">Who is this claim for?</span>
          <select
            className={inputClass}
            value={claimFor}
            onChange={(e) => setClaimFor(e.target.value as ClaimFor)}
            disabled={claimForOptions.length === 0}
          >
            {claimForOptions.length === 0 ? (
              <option value="">Enter a valid employee ID first</option>
            ) : (
              claimForOptions.map((opt) => (
                <option key={`${opt.value}-${opt.memberName}`} value={opt.value}>
                  {opt.label}
                </option>
              ))
            )}
          </select>
          {beneficiary && (
            <p className="mt-1 text-xs text-text-muted">
              Documents should show:{" "}
              <span className="font-medium text-text">{beneficiary.name}</span>
            </p>
          )}
        </label>

        <label className="block sm:col-span-2">
          <span className="text-xs font-medium text-text-muted">
            Patient name on documents (optional)
          </span>
          <input
            className={inputClass}
            value={patientName}
            onChange={(e) => setPatientName(e.target.value)}
            placeholder={beneficiary?.name ?? "As printed on bill or prescription"}
          />
          <p className="mt-1 text-xs text-text-muted">
            Must match the name on uploaded bills. We auto-fill from your selection when possible.
          </p>
        </label>

        <label className="block">
          <span className="text-xs font-medium text-text-muted">Category</span>
          <select className={inputClass} value={category} onChange={(e) => setCategory(e.target.value)}>
            {CATEGORIES.map((c) => (
              <option key={c} value={c}>{c.replace("_", " ")}</option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-xs font-medium text-text-muted">Treatment date</span>
          <input
            type="date"
            className={inputClass}
            value={treatmentDate}
            onChange={(e) => setTreatmentDate(e.target.value)}
            required
          />
        </label>

        <label className="block">
          <span className="text-xs font-medium text-text-muted">Claimed amount (₹)</span>
          <input
            type="text"
            inputMode="numeric"
            className={inputClass}
            value={claimedAmount}
            onChange={(e) => setClaimedAmount(e.target.value.replace(/[^\d]/g, ""))}
            placeholder="1500"
            required
          />
        </label>

        <label className="block">
          <span className="text-xs font-medium text-text-muted">Hospital (optional)</span>
          <input
            className={inputClass}
            value={hospitalName}
            onChange={(e) => setHospitalName(e.target.value)}
            placeholder="Apollo Hospitals"
          />
        </label>

        <label className="block sm:col-span-2">
          <span className="text-xs font-medium text-text-muted">
            Prescription text (optional if uploading images)
          </span>
          <textarea
            className={`${inputClass} font-mono`}
            rows={3}
            value={textDoc}
            onChange={(e) => setTextDoc(e.target.value)}
            placeholder={"Patient: Rajesh Kumar\nDiagnosis: Viral Fever"}
          />
        </label>

        <label className="block sm:col-span-2">
          <span className="text-xs font-medium text-text-muted">Documents</span>
          <input
            type="file"
            multiple
            accept="image/*,.pdf,.txt"
            className="mt-1 w-full rounded-xl border border-dashed border-border bg-surface-muted px-3 py-4 text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-plum-brand file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-white hover:file:bg-plum-brand-dark"
            onChange={(e) => {
              const files = e.target.files;
              if (files) Array.from(files).forEach(addFile);
            }}
          />
          <p className="mt-1 text-xs text-text-muted">
            Required document types for your category are checked after you submit — you will get a
            specific message if something is missing or wrong.
          </p>
        </label>
      </div>

      {documents.length > 0 && (
        <ul className="mt-3 space-y-2">
          {documents.map((d, i) => (
            <li
              key={d.file_id}
              className="flex flex-wrap items-center gap-2 rounded-lg bg-surface-muted px-3 py-2 text-sm"
            >
              <span className="min-w-0 flex-1 truncate font-medium text-text">{d.file_name}</span>
              <select
                className="rounded-lg border border-border px-2 py-1 text-xs"
                value={d.actual_type}
                onChange={(e) => {
                  const val = e.target.value;
                  setDocuments((prev) =>
                    prev.map((doc, idx) => (idx === i ? { ...doc, actual_type: val } : doc))
                  );
                }}
              >
                <option value="">Auto-detect</option>
                {DOC_TYPES.map((t) => (
                  <option key={t} value={t}>{t.replace("_", " ")}</option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => removeDocument(d.file_id)}
                className="rounded-lg px-2 py-1 text-xs font-medium text-rose-600 transition hover:bg-rose-50"
                aria-label={`Remove ${d.file_name}`}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      <button
        type="submit"
        disabled={loading}
        className="mt-5 w-full rounded-xl bg-plum-brand px-4 py-3 text-sm font-semibold text-white transition hover:bg-plum-brand-dark disabled:opacity-50"
      >
        {loading
          ? variant === "ops"
            ? "Running pipeline…"
            : "Processing claim…"
          : variant === "ops"
            ? "Run adjudication"
            : "Check claim decision"}
      </button>

      {formError && <p className="mt-3 text-sm text-rose-600">{formError}</p>}
    </form>
  );
}
