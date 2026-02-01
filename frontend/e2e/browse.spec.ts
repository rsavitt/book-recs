import { test, expect } from "@playwright/test";

test.describe("Browse Page", () => {
  test("should show browse page header", async ({ page }) => {
    await page.goto("/browse");

    await expect(page.getByText("Browse Romantasy")).toBeVisible();
    await expect(page.getByText("Explore our collection")).toBeVisible();
  });

  test("should have filter button", async ({ page }) => {
    await page.goto("/browse");

    await expect(page.getByRole("button", { name: /Filters/i })).toBeVisible();
  });

  test("should toggle filter panel", async ({ page }) => {
    await page.goto("/browse");

    // Click filters button
    await page.getByRole("button", { name: /Filters/i }).click();

    // Filter panel should be visible
    await expect(page.getByText("Filter Books")).toBeVisible();
    await expect(page.getByText("Spice Level")).toBeVisible();
    await expect(page.getByText("Age Category")).toBeVisible();
  });

  test("should have spice level filter options", async ({ page }) => {
    await page.goto("/browse");
    await page.getByRole("button", { name: /Filters/i }).click();

    await expect(page.getByRole("button", { name: "Any" })).toBeVisible();
    await expect(page.getByRole("button", { name: "None" })).toBeVisible();
  });

  test("should have age category filter options", async ({ page }) => {
    await page.goto("/browse");
    await page.getByRole("button", { name: /Filters/i }).click();

    await expect(page.getByRole("button", { name: "YA" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Adult" })).toBeVisible();
  });

  test("should show sign up CTA for non-logged in users", async ({ page }) => {
    await page.goto("/browse");

    // Should show the CTA section
    await expect(page.getByText("Want Personalized Recommendations?")).toBeVisible();
    await expect(page.getByRole("link", { name: "Get Started Free" })).toBeVisible();
  });

  test("should navigate to login when clicking Log in", async ({ page }) => {
    await page.goto("/browse");

    await page.getByRole("link", { name: "Log in" }).click();

    await expect(page).toHaveURL("/login");
  });
});
