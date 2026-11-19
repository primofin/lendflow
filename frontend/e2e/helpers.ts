import { expect } from "@playwright/test";
import type { Browser, Page } from "@playwright/test";

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

export async function registerBorrower(page: Page): Promise<void> {
  await page.goto("/register");
  await page.getByLabel("Email").fill(uniqueEmail("applicant"));
  await page.getByLabel("Password").fill(BORROWER_PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL("/");
  await expect(page.getByText(/\(borrower\)/)).toBeVisible();
}

/** Step 1 of the application form (loan details). Does not press Next. */
export async function fillLoanStep(
  page: Page,
  { amount, term = "12", purpose }: { amount: string; term?: string; purpose?: string },
): Promise<void> {
  await page.getByLabel(/Loan amount/).fill(amount);
  await page.getByLabel("Term").selectOption(term);
  if (purpose) await page.getByLabel(/Purpose of the loan/).fill(purpose);
}

/** Fills the whole form and stops on the last step (review and consent). */
export async function fillApplication(
  page: Page,
  {
    amount,
    term = "12",
    name = "Nguyen Test",
    incomeType = "salaried",
    purpose,
    dateOfBirth = "1990-05-01",
  }: {
    amount: string;
    term?: string;
    name?: string;
    incomeType?: string;
    purpose?: string;
    dateOfBirth?: string;
  },
): Promise<void> {
  await fillLoanStep(page, { amount, term, purpose });
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await page.getByLabel("Full name").fill(name);
  await page.getByLabel("Date of birth").fill(dateOfBirth);
  await page.getByLabel("National ID").fill("012345678901");
  await page.getByLabel("Address").fill("1 Example Street, Hanoi");
  await page.getByLabel("Income type").selectOption(incomeType);
  await page.getByLabel(/Monthly income/).fill("30000000");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page.getByRole("group", { name: "Consent" })).toBeVisible();
}

/** Synthetic files with real magic bytes (the server checks content, not names). */
export function jpeg(seed: number) {
  return {
    name: `scan-${seed}.jpg`,
    mimeType: "image/jpeg",
    buffer: Buffer.concat([Buffer.from([0xff, 0xd8, 0xff, 0xe0]), Buffer.alloc(200, seed)]),
  };
}

export async function submitSmallLoan(
  page: Page,
  opts: { name?: string; incomeType?: string; amount?: string; purpose?: string } = {},
): Promise<string> {
  await registerBorrower(page);
  await page.getByRole("link", { name: "Apply", exact: true }).click();
  await fillApplication(page, { amount: opts.amount ?? "50000000", ...opts });
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Submit application" }).click();
  await expect(page).toHaveURL(/\/applications\/[0-9a-f-]{36}$/);
  return page.url().split("/").pop() as string;
}

export const missingItems = (page: Page) => page.locator('li[data-state="missing"]');

export async function uploadFirstMissing(page: Page, seed: number) {
  const item = missingItems(page).first();
  await item.locator('input[type="file"]').setInputFiles(jpeg(seed));
  await item.getByRole("button", { name: /Upload/ }).click();
}

export const applicantName = (prefix: string) => `${prefix} ${Date.now()}${(counter += 1)}`;

/** Upload every missing document except those whose label matches `skip`. */
export async function uploadAll(page: Page, seed: number, skip?: RegExp) {
  // The checklist loads after the page; counting before it renders would find nothing.
  await expect(missingItems(page).first()).toBeVisible();
  const wanted = skip ? missingItems(page).filter({ hasNotText: skip }) : missingItems(page);
  const count = await wanted.count();
  for (let i = 0; i < count; i += 1) {
    const before = await missingItems(page).count();
    const item = wanted.first();
    await item.locator('input[type="file"]').setInputFiles({
      name: `s${seed + i}.jpg`,
      mimeType: "image/jpeg",
      buffer: Buffer.concat([Buffer.from([0xff, 0xd8, 0xff, 0xe0]), Buffer.alloc(200, seed + i)]),
    });
    await item.getByRole("button", { name: /Upload/ }).click();
    await expect(missingItems(page)).toHaveCount(before - 1);
  }
}

export async function staffPage(browser: Browser, email: string, password: string): Promise<Page> {
  const context = await browser.newContext({ baseURL: "http://localhost:3100" });
  const page = await context.newPage();
  await signIn(page, email, password);
  return page;
}

export async function openFromQueue(page: Page, name: string, status = "IN_REVIEW") {
  await page.getByRole("link", { name: "Queue", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Review queue" })).toBeVisible();
  await page.getByLabel("Status").selectOption(status);
  await page.getByLabel("Order").selectOption("newest");
  await page.getByRole("link", { name }).click();
  await expect(page.getByRole("heading", { name: "Review application" })).toBeVisible();
}

