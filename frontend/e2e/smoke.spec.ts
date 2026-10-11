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

test("a slow-loading saved profile does not overwrite what the user already typed", async ({ page, request }) => {
  // Regression: ProfileForm used to apply the fetched profile unconditionally, clobbering edits made
  // before the response arrived (flaky on slow CI runners; data loss on slow connections).
  const saved = await request.put("/api/profile", {
    data: { sex: "female", age: 30, weight_kg: 60, height_cm: 165, activity: "light", goal: "maintain" },
  });
  expect(saved.ok()).toBeTruthy();

  await page.route("**/api/profile", async (route) => {
    if (route.request().method() === "GET") await new Promise((r) => setTimeout(r, 1500));
    await route.continue();
  });
  const profileLoaded = page.waitForResponse(
    (r) => r.url().endsWith("/api/profile") && r.request().method() === "GET",
  );

  await page.goto("/onboarding");
  await page.getByLabel("Age").fill("16");
  await profileLoaded;
  // let React apply the response before asserting
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));

  await expect(page.getByLabel("Age")).toHaveValue("16");
  await expect(page.getByText("You must be 18 or older")).toBeVisible();
  await expect(page.getByRole("button", { name: "Save profile" })).toBeDisabled();
});
