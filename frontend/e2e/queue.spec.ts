import { expect, test } from "@playwright/test";
import type { PlaywrightWorkerArgs } from "@playwright/test";

import {
  appAlert,
  applicantName,
  OFFICER,
  openFromQueue,
  staffPage,
  STAFF_PASSWORD,
  submitSmallLoan,
  SUPERVISOR,
  uniqueEmail,
  uploadAll,
} from "./helpers";

const BACKEND = "http://localhost:8100";

async function createOfficer(playwright: PlaywrightWorkerArgs["playwright"]) {
  const api = await playwright.request.newContext({ baseURL: BACKEND });
  const login = await api.post("/auth/login", {
    data: { email: SUPERVISOR, password: STAFF_PASSWORD },
  });
  const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
  const email = uniqueEmail("e2e-officer2");
  const created = await api.post("/users", {
    headers,
    data: { email, password: STAFF_PASSWORD, role: "officer" },
  });
  expect(created.ok()).toBe(true);
  return email;
}

test.describe("LF-010 / LF-011 officer queue, file view and claim", () => {
  test("an officer finds a documented file, reads it and claims it; a colleague cannot", async ({
    page,
    browser,
    playwright,
  }) => {
    const name = applicantName("Queue Claim");
    await submitSmallLoan(page, { name });
    await uploadAll(page, 1);
    await expect(page.getByTestId("status")).toHaveText("IN_REVIEW");

    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);
    await openFromQueue(officer, name);
    await expect(officer.getByText("********8901")).toBeVisible();
    await expect(officer.getByTestId("checklist-status")).toHaveText("Complete");
    await expect(officer.getByTestId("holder")).toHaveText("Nobody yet");

    await officer.getByRole("button", { name: "Claim this file" }).click();

    await expect(officer.getByTestId("holder")).toHaveText("You");
    await expect(officer.getByRole("button", { name: "Claim this file" })).toHaveCount(0);

    const colleagueEmail = await createOfficer(playwright);
    const colleague = await staffPage(browser, colleagueEmail, STAFF_PASSWORD);
    await colleague.getByRole("link", { name: "Queue", exact: true }).click();
    await colleague.getByLabel("Order").selectOption("newest");
    await expect(colleague.getByRole("heading", { name: "Review queue" })).toBeVisible();
    await expect(colleague.getByRole("link", { name })).toHaveCount(0);
    await colleague.goto(officer.url());
    await expect(appAlert(colleague)).toContainText(/permission/i);
  });

  test("an officer opens a stored document through an authorised request", async ({
    page,
    browser,
  }) => {
    const name = applicantName("Queue Doc");
    await submitSmallLoan(page, { name });
    await uploadAll(page, 40);

    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);
    await openFromQueue(officer, name);
    // The tab is opened without an opener, so listen for any new page rather than a "popup".
    await expect(officer.getByTestId("documents")).toBeVisible();
    await officer.waitForLoadState("networkidle"); // let the page settle before the click
    const popup = officer.context().waitForEvent("page", { timeout: 8000 });
    await officer.getByRole("button", { name: /^Open / }).first().click({ timeout: 8000 });

    const tab = await popup;
    await tab.waitForURL(/^blob:/, { timeout: 8000 });
  });

  test("declaring a document unavailable flags an exception, assigns a supervisor and queues the file", async ({
    page,
    browser,
  }) => {
    const name = applicantName("Queue Exception");
    await submitSmallLoan(page, { name, incomeType: "freelance" });
    await uploadAll(page, 80, /invoice/i);
    await expect(page.getByTestId("status")).toHaveText("SUBMITTED");

    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);
    await openFromQueue(officer, name, "SUBMITTED");
    await expect(officer.getByTestId("checklist-status")).toHaveText("Incomplete");

    await officer.getByRole("button", { name: /^No .* available$/ }).click();

    await expect(officer.getByTestId("checklist-status")).toHaveText("Exception declared");
    await expect(officer.getByTestId("flags")).toContainText("Exception");
    await expect(officer.getByTestId("holder")).toContainText("supervisor assigned");
    await expect(officer.getByTestId("status")).toHaveText("IN_REVIEW");

    await officer.getByRole("link", { name: "Queue", exact: true }).click();
    await officer.getByLabel("Flag").selectOption("exception");
    await officer.getByLabel("Order").selectOption("newest");
    await expect(officer.getByRole("link", { name })).toBeVisible();
  });

  test("a supervisor sees the file but has no claim or exception buttons", async ({
    page,
    browser,
  }) => {
    const name = applicantName("Queue Supervisor");
    await submitSmallLoan(page, { name });
    await uploadAll(page, 120);

    const supervisor = await staffPage(browser, SUPERVISOR, STAFF_PASSWORD);
    await openFromQueue(supervisor, name);

    await expect(supervisor.getByText("********8901")).toBeVisible();
    await expect(supervisor.getByRole("button", { name: "Claim this file" })).toHaveCount(0);
  });

  test("a borrower cannot open the queue", async ({ page }) => {
    await submitSmallLoan(page, { name: applicantName("Queue Borrower") });

    await page.goto("/queue");

    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
    await expect(page.getByRole("link", { name: "Queue", exact: true })).toHaveCount(0);
  });
});
