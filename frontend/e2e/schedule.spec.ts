import { expect, test } from "@playwright/test";

import {
  applicantName,
  OFFICER,
  openFromQueue,
  staffPage,
  STAFF_PASSWORD,
  submitSmallLoan,
  SUPERVISOR,
  uploadAll,
} from "./helpers";

test.describe("LF-014 repayment schedule and reminders", () => {
  test("once approved the borrower sees the full schedule; before that there is none", async ({
    page,
    browser,
  }) => {
    const name = applicantName("Schedule Person");
    await submitSmallLoan(page, { name });
    await uploadAll(page, 1);
    await expect(page.getByTestId("status")).toHaveText("IN_REVIEW");
    await expect(page.getByTestId("schedule")).toHaveCount(0);

    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);
    await openFromQueue(officer, name);
    await officer.getByLabel("Your decision").selectOption("approve");
    await officer.getByRole("button", { name: /^Review (decision|correction)$/ }).click();
    await officer.getByRole("dialog").getByRole("button", { name: "Confirm and record" }).click();
    await expect(officer.getByTestId("status")).toHaveText("APPROVED");

    await page.reload();
    await expect(page.getByTestId("status")).toHaveText("APPROVED");
    const rows = page.getByTestId("schedule-table").getByRole("row");
    await expect(rows).toHaveCount(13); // header + 12 monthly instalments
    await expect(page.getByTestId("schedule-summary")).toContainText("a month at 14% a year, for 12 months");
    await expect(rows.nth(12)).toContainText("0 VND"); // nothing owed after the last one
    await expect(page.getByText(/Payments are not recorded/)).toBeVisible();
  });

  test("a borrower can switch repayment reminders off and on, and it is remembered", async ({ page }) => {
    await submitSmallLoan(page, { name: applicantName("Settings Person") });

    await page.getByRole("link", { name: "Settings", exact: true }).click();
    const box = page.getByRole("checkbox", { name: "Email me before each repayment is due" });
    await expect(box).toBeChecked();

    await box.uncheck();
    await expect(page.getByTestId("settings-saved")).toHaveText("Reminders are off.");
    await page.reload();
    await expect(box).not.toBeChecked();

    await box.check();
    await expect(page.getByTestId("settings-saved")).toHaveText("Reminders are on.");
    await page.reload();
    await expect(box).toBeChecked();
  });

  test("a supervisor can queue the due reminders; nothing is due yet so none are sent", async ({ browser }) => {
    const supervisor = await staffPage(browser, SUPERVISOR, STAFF_PASSWORD);
    await supervisor.goto("/admin/dashboard");

    await supervisor.getByRole("button", { name: "Send due reminders now" }).click();

    await expect(supervisor.getByTestId("reminders-result")).toHaveText("0 reminders queued.");
  });

  test("staff have no Settings link and cannot open the borrower's settings page", async ({ browser }) => {
    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);

    await expect(officer.getByRole("link", { name: "Settings", exact: true })).toHaveCount(0);
    await officer.goto("/settings");
    await expect(officer.getByText("You do not have access to this page.")).toBeVisible();
  });
});
