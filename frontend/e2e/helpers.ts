import { expect } from "@playwright/test";
import type { Page } from "@playwright/test";

export const STAFF_PASSWORD = process.env.E2E_PASSWORD ?? "e2e-password-123";
export const SUPERVISOR = "e2e-supervisor@lendflow.example.com";
export const OFFICER = "e2e-officer@lendflow.example.com";
export const BORROWER_PASSWORD = "borrower-password-1";

let counter = 0;
/** A fresh synthetic address per test; the database is shared across the run. */
export function uniqueEmail(prefix: string): string {
  counter += 1;
  return `${prefix}-${Date.now()}-${counter}@example.com`;
}

export async function logIn(
  page: Page,
  email: string,
  password: string,
): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Log in" }).click();
}

export async function expectLoggedInAs(
  page: Page,
  email: string,
  role: string,
): Promise<void> {
  await expect(page.getByText(`${email} (${role})`)).toBeVisible();
}

export async function logOut(page: Page): Promise<void> {
  await page.getByRole("button", { name: "Log out" }).click();
  await expect(page).toHaveURL(/\/login$/);
}

/** The app's own alerts. Next.js also renders an empty role="alert" route announcer. */
export function appAlert(page: Page) {
  return page.locator('[role="alert"]:not(#__next-route-announcer__)');
}

/** Log in and wait until the redirect home has finished, so later clicks cannot race it. */
export async function signIn(
  page: Page,
  email: string,
  password: string,
): Promise<void> {
  await logIn(page, email, password);
  await expect(page).toHaveURL("/");
  await expectLoggedInAs(
    page,
    email,
    email.includes("supervisor") ? "supervisor" : "officer",
  );
}
