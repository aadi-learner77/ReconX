import { expect, test } from "@playwright/test";
import path from "path";
import { fileURLToPath } from "url";

const DEMO_PASSWORD = process.env.SEED_DEFAULT_PASSWORD || "ReconXDemo#2026!";
const __dirname = path.dirname(fileURLToPath(import.meta.url));

test("smoke: login -> upload sample invoice -> inspect/verify -> reconcile -> see exception", async ({
  page,
}) => {
  await page.goto("/login");
  await page.fill("#email", "operator@reconx-demo.com");
  await page.fill("#password", DEMO_PASSWORD);
  await page.click('button[type="submit"]');

  await expect(page.getByText("Finance Operations Dashboard")).toBeVisible();

  // Navigate to Documents and upload sample_invoice_at01.pdf
  await page.click('a[href="/documents"]');
  await expect(page.getByText("Document Workspace")).toBeVisible();

  const samplePath = path.resolve(__dirname, "../../sample_data/sample_invoice_at01.pdf");
  await page.setInputFiles('[data-testid="file-upload-input"]', samplePath);
  await expect(page.getByRole("heading", { name: "sample_invoice_at01.pdf" })).toBeVisible({
    timeout: 15000,
  });
  await expect(page.getByLabel("Edit document_number")).toHaveValue("INV-BPC-9901", {
    timeout: 15000,
  });
  await page.fill('[aria-label="Edit vendor_name"]', "Bharat Precision Components Pvt. Ltd.");
  await page.click('button:has-text("Save Corrections")');
  await expect(page.getByText("Field correction saved with audit trail.")).toBeVisible();

  // Navigate to Transactions, search for AT-02 over-billing scenario, reconcile, and see EXCEPTION
  await page.click('a[href="/transactions"]');
  await page.fill('[aria-label="Search PO or vendor"]', "PO-2026-0002");
  await expect(page.getByText("PO-2026-0002")).toBeVisible({ timeout: 10000 });
  await page.click('a:has-text("PO-2026-0002")');
  await expect(page.getByRole("button", { name: "Reconcile" })).toBeVisible();
  await page.click('button:has-text("Reconcile")');
  await expect(page.getByText("R-QTY-01").first()).toBeVisible({ timeout: 10000 });
  await expect(page.getByText(/QTY_OVER_BILLED/).first()).toBeVisible();
});
