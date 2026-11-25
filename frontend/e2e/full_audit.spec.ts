import { expect, test } from "@playwright/test";

const DEMO_PASSWORD = process.env.SEED_DEFAULT_PASSWORD || "ReconXDemo#2026!";

test("full website audit across all routes, workflows, RBAC, and viewports", async ({
  page,
}) => {
  const consoleErrors: string[] = [];
  const pageErrors: string[] = [];
  const failedResponses: { url: string; status: number }[] = [];
  let allow401 = true;

  page.on("console", (msg) => {
    if (msg.type() === "error") {
      consoleErrors.push(msg.text());
    }
  });
  page.on("pageerror", (err) => {
    pageErrors.push(err.message);
  });
  page.on("response", (res) => {
    if (res.status() >= 400) {
      if (allow401 && res.url().includes("/auth/login") && res.status() === 401) {
        return;
      }
      failedResponses.push({ url: res.url(), status: res.status() });
    }
  });

  // 1. Login validation & invalid password check
  await page.goto("/login");
  await page.fill("#email", "operator@reconx-demo.com");
  await page.fill("#password", "wrongpass123");
  await page.click('button[type="submit"]');
  await expect(page.locator("text=/invalid|incorrect|failed|unauthorized/i").first()).toBeVisible({
    timeout: 10000,
  });

  // Valid login as operator
  allow401 = false;
  await page.fill("#password", DEMO_PASSWORD);
  await page.click('button[type="submit"]');
  await expect(page.getByText("Finance Operations Dashboard")).toBeVisible({ timeout: 10000 });
  await page.screenshot({ path: "playwright-report/audit-dashboard.png", fullPage: true });

  // Reload persistence check
  await page.reload();
  await expect(page.getByText("Finance Operations Dashboard")).toBeVisible({ timeout: 10000 });

  // 2. Documents page
  await page.click('a[href="/documents"]');
  await expect(page.getByText("Document Workspace")).toBeVisible();
  await page.screenshot({ path: "playwright-report/audit-documents.png", fullPage: true });

  // 3. Transactions -> PO-2026-0002 -> Reconcile -> Evidence Graph
  await page.click('a[href="/transactions"]');
  await page.fill('[aria-label="Search PO or vendor"]', "PO-2026-0002");
  await expect(page.getByText("PO-2026-0002")).toBeVisible({ timeout: 10000 });
  await page.click('a:has-text("PO-2026-0002")');
  await expect(page.getByRole("button", { name: "Reconcile" })).toBeVisible();
  await page.click('button:has-text("Reconcile")');
  await expect(page.getByText("R-QTY-01").first()).toBeVisible({ timeout: 10000 });
  await expect(page.locator(".react-flow").first()).toBeVisible({ timeout: 10000 });
  await page.screenshot({ path: "playwright-report/audit-transaction-detail.png", fullPage: true });

  // 4. Exceptions -> Run Investigation
  await page.click('a[href="/exceptions"]');
  await expect(page.locator("a[href^='/exceptions/']").first()).toBeVisible({ timeout: 10000 });
  await page.locator("a[href^='/exceptions/']").first().click();
  await expect(page.getByRole("button", { name: /Run Investigation/i })).toBeVisible();
  await page.click('button:has-text("Run Investigation")');
  await expect(page.getByText(/Investigation completed/i)).toBeVisible({ timeout: 25000 });
  await page.screenshot({ path: "playwright-report/audit-exception-detail.png", fullPage: true });

  // 5. Finance Copilot
  await page.click('button:has-text("Finance Copilot")');
  await page.fill('input[placeholder*="Ask" i], textarea[placeholder*="Ask" i]', "What is our cash forecast?");
  await page.click('button:has-text("Ask"), button:has-text("Send")');
  await expect(page.getByText(/Cash obligation summary/i)).toBeVisible({ timeout: 10000 });

  await page.fill('input[placeholder*="Ask" i], textarea[placeholder*="Ask" i]', "approve PO-2026-0001");
  await page.click('button:has-text("Ask"), button:has-text("Send")');
  await expect(page.getByText(/strictly read-only/i)).toBeVisible({ timeout: 10000 });

  // 6. Vendors & Cash Obligations
  await page.click('a[href="/vendors"]');
  await expect(page.locator("h1").first()).toBeVisible();
  await page.screenshot({ path: "playwright-report/audit-vendors.png", fullPage: true });

  await page.click('a[href="/cash"]');
  await expect(page.locator("h1").first()).toBeVisible();
  await page.screenshot({ path: "playwright-report/audit-cash.png", fullPage: true });

  // 6b. Agent Harness Explorer (/agent-harness)
  await page.click('a[href="/agent-harness"]');
  await expect(page.getByText("Inside the ReconX Intelligence Engine")).toBeVisible();
  await expect(page.getByText(/AI RECOMMENDATION ≠ FINANCIAL AUTHORIZATION/)).toBeVisible();
  await expect(page.getByText("Live Execution Trace Explorer")).toBeVisible();
  await page.screenshot({ path: "playwright-report/audit-agent-harness.png", fullPage: true });

  // 6c. Financial Obligation Graph (/obligation-graph)
  await page.click('a[href="/obligation-graph"]');
  await expect(page.getByText("Financial Obligation Graph")).toBeVisible();
  await expect(page.getByText("Ordered Qty")).toBeVisible({ timeout: 10000 });
  await page.click('button:has-text("Evidence View")');
  await page.click('button:has-text("Obligation View")');
  await page.screenshot({ path: "playwright-report/audit-obligation-graph.png", fullPage: true });

  // 7. Sign out & Admin login -> Audit Explorer & Admin Settings
  await page.click('button:has-text("Sign out")');
  await expect(page.locator("#email")).toBeVisible();
  await page.fill("#email", "admin@reconx-demo.com");
  await page.fill("#password", DEMO_PASSWORD);
  await page.click('button[type="submit"]');
  await expect(page.getByText("Finance Operations Dashboard")).toBeVisible({ timeout: 10000 });

  await page.click('a[href="/audit"]');
  await expect(page.locator("h1").first()).toBeVisible();
  await page.screenshot({ path: "playwright-report/audit-audit-explorer.png", fullPage: true });

  await page.click('a[href="/admin"]');
  await expect(page.locator("h1").first()).toBeVisible();
  await page.screenshot({ path: "playwright-report/audit-admin.png", fullPage: true });

  // 7b. Policy Studio (/policy-studio) & Executive Brief (/executive-brief)
  await page.click('a[href="/policy-studio"]');
  await expect(page.getByRole("heading", { name: "Policy Studio" })).toBeVisible();
  await expect(page.getByText("POL-SYS-DUP")).toBeVisible({ timeout: 10000 });
  await page.screenshot({ path: "playwright-report/audit-policy-studio.png", fullPage: true });

  await page.click('a[href="/executive-brief"]');
  await expect(page.getByRole("heading", { name: "Executive Boardroom Brief" })).toBeVisible();
  await page.click('button:has-text("Generate Executive Brief")');
  await expect(page.getByText("Top Three Urgent Exceptions")).toBeVisible({ timeout: 10000 });
  await page.screenshot({ path: "playwright-report/audit-executive-brief.png", fullPage: true });

  // 8. Mobile viewport check (390x844)
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByText("Finance Operations Dashboard")).toBeVisible({ timeout: 10000 });
  await page.screenshot({ path: "playwright-report/audit-mobile.png", fullPage: true });

  expect(pageErrors, `Uncaught page errors: ${pageErrors.join("; ")}`).toEqual([]);
  expect(failedResponses, `Unexpected >=400 responses: ${JSON.stringify(failedResponses)}`).toEqual([]);
});
