/** Demo policy roster — mirrors assignment/policy_terms.json (do not extend here). */
export type PolicyMember = {
  member_id: string;
  name: string;
  relationship: string;
  primary_member_id?: string;
};

export type ClaimFor = "SELF" | "SPOUSE" | "CHILD" | "PARENT";

export type ClaimForOption = {
  value: ClaimFor;
  label: string;
  memberName: string;
};

const RELATIONSHIP_LABELS: Record<string, string> = {
  SPOUSE: "Spouse",
  CHILD: "Child",
  PARENT: "Parent",
};

const POLICY_MEMBERS: PolicyMember[] = [
  { member_id: "EMP001", name: "Rajesh Kumar", relationship: "SELF" },
  { member_id: "EMP002", name: "Priya Singh", relationship: "SELF" },
  { member_id: "EMP003", name: "Amit Verma", relationship: "SELF" },
  { member_id: "EMP004", name: "Sneha Reddy", relationship: "SELF" },
  { member_id: "EMP005", name: "Vikram Joshi", relationship: "SELF" },
  { member_id: "EMP006", name: "Kavita Nair", relationship: "SELF" },
  { member_id: "EMP007", name: "Suresh Patil", relationship: "SELF" },
  { member_id: "EMP008", name: "Ravi Menon", relationship: "SELF" },
  { member_id: "EMP009", name: "Anita Desai", relationship: "SELF" },
  { member_id: "EMP010", name: "Deepak Shah", relationship: "SELF" },
  { member_id: "DEP001", name: "Sunita Kumar", relationship: "SPOUSE", primary_member_id: "EMP001" },
  { member_id: "DEP002", name: "Arjun Kumar", relationship: "CHILD", primary_member_id: "EMP001" },
];

export function resolvePolicyMember(memberId: string): PolicyMember | undefined {
  const id = memberId.trim().toUpperCase();
  return POLICY_MEMBERS.find((m) => m.member_id === id);
}

export function lookupEmployee(employeeId: string): PolicyMember | undefined {
  const member = resolvePolicyMember(employeeId);
  if (!member) return undefined;
  if (member.primary_member_id) {
    return POLICY_MEMBERS.find((m) => m.member_id === member.primary_member_id);
  }
  return member.relationship === "SELF" ? member : undefined;
}

/** Who can be selected for a claim once employee / dependent ID is entered. */
export function claimForOptionsForEmployee(employeeId: string): ClaimForOption[] {
  const member = resolvePolicyMember(employeeId);
  if (!member) return [];

  if (member.primary_member_id) {
    return [{ value: "SELF", label: `Myself — ${member.name}`, memberName: member.name }];
  }

  const options: ClaimForOption[] = [
    { value: "SELF", label: `Myself — ${member.name}`, memberName: member.name },
  ];

  const dependents = POLICY_MEMBERS.filter((m) => m.primary_member_id === member.member_id);
  for (const dep of dependents) {
    const rel = dep.relationship.toUpperCase();
    if (rel !== "SPOUSE" && rel !== "CHILD" && rel !== "PARENT") continue;
    const relLabel = RELATIONSHIP_LABELS[rel] ?? rel;
    options.push({
      value: rel as ClaimFor,
      label: `${relLabel} — ${dep.name}`,
      memberName: dep.name,
    });
  }

  return options;
}

export function familyForEmployee(
  employeeId: string,
  claimFor: string
): PolicyMember | undefined {
  const member = resolvePolicyMember(employeeId);
  if (!member) return undefined;

  if (member.primary_member_id) {
    return claimFor.toUpperCase() === "SELF" ? member : undefined;
  }

  const empId = member.member_id;
  const rel = claimFor.toUpperCase();
  if (rel === "SELF") return member;
  return POLICY_MEMBERS.find(
    (m) => m.primary_member_id === empId && m.relationship === rel
  );
}