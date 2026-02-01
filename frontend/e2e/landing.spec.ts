import { test, expect } from "@playwright/test";

test.describe("Landing Page", () => {
  test("should display hero section", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Find Your Next Favorite")).toBeVisible();
    await expect(page.getByText("Romantasy")).toBeVisible();
  });

  test("should display navigation", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Romantasy Recs")).toBeVisible();
    await expect(page.getByRole("link", { name: "Log in" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Get Started" })).toBeVisible();
  });

  test("should display how it works section", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("How It Works")).toBeVisible();
    await expect(page.getByText("Import Your Library")).toBeVisible();
    await expect(page.getByText("Find Your People")).toBeVisible();
    await expect(page.getByText("Get Recommendations")).toBeVisible();
  });

  test("should display filter features section", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Filter By What Matters")).toBeVisible();
    await expect(page.getByText("Spice Level")).toBeVisible();
    await expect(page.getByText("Tropes")).toBeVisible();
    await expect(page.getByText("YA or Adult")).toBeVisible();
  });

  test("should display CTA section", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Ready to Find Your Next Read?")).toBeVisible();
    await expect(page.getByRole("link", { name: "Get Started Free" })).toBeVisible();
  });

  test("should navigate to register on Get Started click", async ({ page }) => {
    await page.goto("/");

    // Click the hero CTA
    await page.getByRole("link", { name: "Import Your Library" }).click();

    await expect(page).toHaveURL("/register");
  });

  test("should navigate to browse on Browse Romantasy click", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("link", { name: "Browse Romantasy" }).click();

    await expect(page).toHaveURL("/browse");
  });

  test("should navigate to login on Log in click", async ({ page }) => {
    await page.goto("/");

    await page.getByRole("link", { name: "Log in" }).click();

    await expect(page).toHaveURL("/login");
  });

  test("should be responsive on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto("/");

    // Hero should still be visible
    await expect(page.getByText("Find Your Next Favorite")).toBeVisible();

    // Navigation should be accessible
    await expect(page.getByText("Romantasy Recs")).toBeVisible();
  });
});
