import { test, expect } from "@playwright/test";

test.describe("Authentication", () => {
  test.describe("Registration", () => {
    test("should show registration form", async ({ page }) => {
      await page.goto("/register");

      await expect(page.getByText("Create your account")).toBeVisible();
      await expect(page.getByLabel("Email address")).toBeVisible();
      await expect(page.getByLabel("Username")).toBeVisible();
      await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
      await expect(page.getByLabel("Confirm Password")).toBeVisible();
    });

    test("should validate password match", async ({ page }) => {
      await page.goto("/register");

      await page.getByLabel("Email address").fill("test@example.com");
      await page.getByLabel("Username").fill("testuser");
      await page.getByLabel("Password", { exact: true }).fill("password123");
      await page.getByLabel("Confirm Password").fill("differentpassword");

      await page.getByRole("button", { name: "Create account" }).click();

      await expect(page.getByText("Passwords do not match")).toBeVisible();
    });

    test("should validate password length", async ({ page }) => {
      await page.goto("/register");

      await page.getByLabel("Email address").fill("test@example.com");
      await page.getByLabel("Username").fill("testuser");
      await page.getByLabel("Password", { exact: true }).fill("short");
      await page.getByLabel("Confirm Password").fill("short");

      await page.getByRole("button", { name: "Create account" }).click();

      await expect(page.getByText("at least 8 characters")).toBeVisible();
    });

    test("should have link to login", async ({ page }) => {
      await page.goto("/register");

      await page.getByText("Sign in").click();

      await expect(page).toHaveURL("/login");
    });
  });

  test.describe("Login", () => {
    test("should show login form", async ({ page }) => {
      await page.goto("/login");

      await expect(page.getByText("Sign in to your account")).toBeVisible();
      await expect(page.getByLabel("Email address")).toBeVisible();
      await expect(page.getByLabel("Password")).toBeVisible();
    });

    test("should have link to registration", async ({ page }) => {
      await page.goto("/login");

      await page.getByText("Create an account").click();

      await expect(page).toHaveURL("/register");
    });

    test("should have link to forgot password", async ({ page }) => {
      await page.goto("/login");

      await page.getByText("Forgot your password?").click();

      await expect(page).toHaveURL("/forgot-password");
    });
  });

  test.describe("Forgot Password", () => {
    test("should show forgot password form", async ({ page }) => {
      await page.goto("/forgot-password");

      await expect(page.getByText("Reset your password")).toBeVisible();
      await expect(page.getByLabel("Email address")).toBeVisible();
      await expect(page.getByRole("button", { name: "Send reset link" })).toBeVisible();
    });

    test("should have link back to login", async ({ page }) => {
      await page.goto("/forgot-password");

      await page.getByText("Back to login").click();

      await expect(page).toHaveURL("/login");
    });
  });
});
