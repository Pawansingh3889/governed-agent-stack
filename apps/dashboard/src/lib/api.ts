const SCOUT_URL = process.env.NEXT_PUBLIC_SCOUT_URL ?? "http://localhost:8080";
const SQL_STEWARD_URL = process.env.NEXT_PUBLIC_SQL_STEWARD_URL ?? "http://localhost:8081";
const ELENCHUS_URL = process.env.NEXT_PUBLIC_ELENCHUS_URL ?? "http://localhost:8000";
const BLACKBOX_URL = process.env.NEXT_PUBLIC_BLACKBOX_URL ?? "http://localhost:8082";

async function safeFetch(url: string, init?: RequestInit) {
  try {
    const res = await fetch(url, { ...init, signal: AbortSignal.timeout(5000) });
    if (!res.ok) throw new Error(`${res.status}`);
    return await res.json();
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "unknown";
    return { error: msg };
  }
}

export interface ComponentStatus {
  name: string;
  role: string;
  url: string;
  online: boolean;
}

export async function getComponentStatuses(): Promise<ComponentStatus[]> {
  const components = [
    { name: "schema-scout", role: "Schema Discovery", url: SCOUT_URL },
    { name: "drift-gate", role: "Schema Drift Detection", url: SCOUT_URL },
    { name: "sql-steward", role: "Governed Query Gateway", url: SQL_STEWARD_URL },
    { name: "elenchus", role: "Survey Service", url: ELENCHUS_URL },
    { name: "agent-blackbox", role: "Audit Ledger", url: BLACKBOX_URL },
  ];

  const results = await Promise.all(
    components.map(async (c) => {
      const data = await safeFetch(`${c.url}/health`);
      return { ...c, online: !data.error };
    })
  );

  return results;
}

export async function getSchemaTables() {
  return safeFetch(`${SCOUT_URL}/api/v1/schema/tables`);
}

export async function getSchemaDrift() {
  return safeFetch(`${SCOUT_URL}/api/v1/drift`);
}

export async function getSqlStewardEntities() {
  return safeFetch(`${SQL_STEWARD_URL}/api/v1/entities`);
}

export async function lintSql(sql: string) {
  return safeFetch(`${SQL_STEWARD_URL}/api/v1/lint`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sql }),
  });
}

export async function getSurveys() {
  return safeFetch(`${ELENCHUS_URL}/api/v1/templates/published`);
}

export async function getAuditLogs() {
  return safeFetch(`${BLACKBOX_URL}/api/v1/entries`);
}
