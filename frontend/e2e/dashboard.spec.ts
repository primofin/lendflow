import { expect, test } from "@playwright/test";

import { OFFICER, staffPage, STAFF_PASSWORD, SUPERVISOR } from "./helpers";

test.describe("LF-019 operations dashboard", () => {
  test("a supervisor sees the figures and chart, switches range, and views the table", async ({ browser }) => {
    const supervisor = await staffPage(browser, SUPERVISOR, STAFF_PASSWORD);

    await supervisor.getByRole("link", { name: "Dashboard", exact: true }).click();
    await expect(supervisor.getByRole("heading", { name: "Operations dashboard" })).toBeVisible();
    await expect(supervisor.getByTestId("value-approval-rate")).toBeVisible();
    await expect(supervisor.getByTestId("value-overdue")).toBeVisible();
    await expect(supervisor.getByTestId("status-chart").getByRole("listitem")).toHaveCount(7);
    const shown = await supervisor.getByTestId("range-shown").innerText();

    await supervisor.getByRole("button", { name: "Last 7 days" }).click();
    await expect(supervisor.getByTestId("range-shown")).not.toHaveText(shown);
    await expect(supervisor.getByRole("button", { name: "Last 7 days" })).toHaveAttribute("aria-pressed", "true");

    await supervisor.getByRole("button", { name: "Show as table" }).click();
    await expect(supervisor.getByTestId("status-table")).toContainText("In review");
    await expect(supervisor.getByTestId("status-table")).toContainText("Needs information");

    await supervisor.getByLabel("From", { exact: true }).fill("2026-03-01");
    await supervisor.getByLabel("To", { exact: true }).fill("2026-02-01");
    await supervisor.getByRole("button", { name: "Apply range" }).click();
    await expect(supervisor.getByRole("alert").filter({ hasText: "must not be after" })).toBeVisible();
  });

  test("an officer has no Dashboard link and cannot open the page", async ({ browser }) => {
    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);

    await expect(officer.getByRole("link", { name: "Dashboard", exact: true })).toHaveCount(0);
    await officer.goto("/admin/dashboard");
    await expect(officer.getByText("You do not have access to this page.")).toBeVisible();
  });
});
