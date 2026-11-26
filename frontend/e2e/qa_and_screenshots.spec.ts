import { expect, test } from "@playwright/test";
import path from "path";

const SCREENSHOT_DIR = path.resolve(process.cwd(), "../docs/screenshots");
const DEMO_PASSWORD = process.env.SEED_DEFAULT_PASSWORD || "ReconXDemo#2026!";

function parseRgb(rgb: string): [number, number, number] {
  const m = rgb.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!m) return [0, 0, 0];
  return [Number(m[1]), Number(m[2]), Number(m[3])];
}

function relativeLuminance([r, g, b]: [number, number, number]): number {
  const toLinear = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  };
  return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
}

function contrastRatio(fg: string, bg: string): number {
  const l1 = relativeLuminance(parseRgb(fg));
  const l2 = relativeLuminance(parseRgb(bg));
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

test("WCAG AA status pills, keyboard navigation, CLS, responsive viewports, and 1440x900 screenshots", async ({
  page,
}) => {
  // 1. WCAG AA Contrast Check on /dev/ui-kit (Light & Dark)
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto("/dev/ui-kit");
  await expect(page.getByText("ReconX UI Kit")).toBeVisible();

  for (const mode of ["light", "dark"] as const) {
    await page.evaluate((m) => {
      document.documentElement.setAttribute("data-theme", m);
      document.documentElement.classList.toggle("dark", m === "dark");
    }, mode);
    await page.waitForTimeout(150);

    const pills = await page.locator('[data-testid="status-badge"]').evaluateAll((els) =>
      els.map((el) => {
        const cs = getComputedStyle(el);
        return {
          text: el.textContent?.trim() || "",
          color: cs.color,
          backgroundColor: cs.backgroundColor,
        };
      })
    );
    expect(pills.length).toBeGreaterThanOrEqual(5);
    for (const pill of pills) {
      const ratio = contrastRatio(pill.color, pill.backgroundColor);
      expect(
        ratio,
        `${mode} mode pill "${pill.text}" contrast ${ratio.toFixed(2)} < 4.5 (${pill.color} on ${pill.backgroundColor})`
      ).toBeGreaterThanOrEqual(4.5);
    }
  }

  // Reset to light mode and sign in
  await page.evaluate(() => {
    localStorage.setItem("reconx_theme", "light");
    document.documentElement.setAttribute("data-theme", "light");
    document.documentElement.classList.remove("dark");
  });

  await page.goto("/login");
  await page.fill("#email", "admin@reconx-demo.com");
  await page.fill("#password", DEMO_PASSWORD);
  await page.click('button[type="submit"]');
  await expect(page.getByText("Finance Operations Dashboard")).toBeVisible({ timeout: 10000 });

  // 2. Measure CLS on Dashboard load
  const clsValue = await page.evaluate(async () => {
    let cls = 0;
    const obs = new PerformanceObserver((list) => {
      for (const entry of list.getEntries() as any[]) {
        if (!entry.hadRecentInput) cls += entry.value;
      }
    });
    obs.observe({ type: "layout-shift", buffered: true });
    await new Promise((r) => setTimeout(r, 800));
    obs.disconnect();
    return cls;
  });
  expect(clsValue, `Measured CLS=${clsValue}`).toBeLessThan(0.1);

  // 3. Full keyboard navigation (? shortcuts, / command palette, g e exceptions, g d dashboard)
  await page.keyboard.press("Shift+?");
  await expect(page.getByRole("dialog", { name: "Keyboard Shortcuts" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog", { name: "Keyboard Shortcuts" })).toBeHidden();

  await page.keyboard.press("/");
  await expect(
    page.getByPlaceholder("Jump to pages, POs (PO-2026-0002), or vendors...")
  ).toBeVisible();
  await page.keyboard.press("Escape");

  await page.keyboard.press("g");
  await page.keyboard.press("e");
  await expect(page).toHaveURL(/\/exceptions/);

  await page.keyboard.press("g");
  await page.keyboard.press("d");
  await expect(page).toHaveURL(/\/$/);

  // 4. Responsive viewports check (360, 768, 1280, 1920)
  for (const vp of [
    { width: 360, height: 800 },
    { width: 768, height: 1024 },
    { width: 1280, height: 800 },
    { width: 1920, height: 1080 },
  ]) {
    await page.setViewportSize(vp);
    await page.waitForTimeout(200);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth
    );
    expect(overflow, `Horizontal overflow at ${vp.width}x${vp.height}: ${overflow}px`).toBeLessThanOrEqual(2);
  }

  // 5. Re-capture 1440x900 screenshots (Light & Dark)
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "audit-dashboard.png") });

  await page.evaluate(() => {
    document.documentElement.setAttribute("data-theme", "dark");
    document.documentElement.classList.add("dark");
  });
  await page.waitForTimeout(250);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "audit-dashboard-dark.png") });

  // Switch back to light for remaining screenshots
  await page.evaluate(() => {
    document.documentElement.setAttribute("data-theme", "light");
    document.documentElement.classList.remove("dark");
  });

  await page.goto("/transactions");
  const po2 = page.getByRole("link", { name: "PO-2026-0002" }).first();
  if (await po2.isVisible()) {
    await po2.click();
    await expect(page.getByRole("heading", { name: "PO-2026-0002" })).toBeVisible();
    await page.waitForTimeout(500);
    await page.screenshot({ path: path.join(SCREENSHOT_DIR, "audit-transaction-detail.png") });
  }

  await page.goto("/agent-harness");
  await expect(page.getByText("Inside the ReconX Intelligence Engine")).toBeVisible();
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "audit-agent-harness.png") });

  await page.goto("/obligation-graph");
  await expect(page.getByText("Financial Obligation Graph")).toBeVisible();
  await page.waitForTimeout(600);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "audit-obligation-graph.png") });

  await page.goto("/policy-studio");
  await expect(page.getByRole("heading", { name: "Policy Studio" })).toBeVisible();
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "audit-policy-studio.png") });

  await page.goto("/executive-brief");
  await expect(page.getByRole("heading", { name: "Executive Boardroom Brief" })).toBeVisible();
  await page.waitForTimeout(400);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, "audit-executive-brief.png") });
});
