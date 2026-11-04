const { test, expect } = require("@playwright/test");

test("customer can open the catalog after login", async ({ page }) => {
  await page.goto("/login");
  await page.getByRole("button", { name: "Customer · Priya" }).click();
  await expect(page.getByRole("heading", { name: /home/i })).toBeVisible();
  await page.getByRole("link", { name: "Book a service" }).click();
  await expect(page.getByRole("heading", { name: "Services" })).toBeVisible();
  await page.screenshot({ path: "docs/evidence/e2e-services.png" });
});
