import { expect, test } from "@playwright/test";

test("chat streams specialist chips and a final answer", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Message").fill("plan my week");
  await page.getByRole("button", { name: "Send" }).click();
  await expect(page.getByText("(demo mode) You asked: plan my week")).toBeVisible();
  await expect(page.getByText("Nutrition", { exact: true })).toBeVisible();
  await expect(page.getByText("Sleep & recovery", { exact: true })).toBeVisible();
});

test("crisis message shows the support card, not a model answer", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Message").fill("I want to kill myself");
  await page.getByRole("button", { name: "Send" }).click();
  const alert = page.locator("section[role=alert]");
  await expect(alert).toContainText("988");
  await expect(page.getByText("(demo mode)")).toHaveCount(0);
});

test("profile preview, check-in and chart", async ({ page }) => {
  await page.goto("/onboarding");
  await expect(page.getByText("Estimated daily targets")).toBeVisible();
  await page.getByRole("button", { name: "Save profile" }).click();
  await expect(page.getByText("Saved.")).toBeVisible();

  await page.goto("/progress");
  await page.getByLabel("Sleep (h)").fill("7.5");
  await page.getByRole("button", { name: "Save check-in" }).click();
  await expect(page.getByText("Check-in saved.")).toBeVisible();
  await expect(page.getByRole("img", { name: /Sleep trend/ })).toBeVisible();
});

test("under-18 age is flagged", async ({ page }) => {
  await page.goto("/onboarding");
  await page.getByLabel("Age").fill("16");
  await expect(page.getByText("You must be 18 or older")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save profile" })).toBeDisabled();
});
