import { readFileSync } from "node:fs";

import { expect, test } from "@playwright/test";

import {
  applicantName,
  OFFICER,
  staffPage,
  STAFF_PASSWORD,
  submitSmallLoan,
  SUPERVISOR,
} from "./helpers";

test.describe("LF-018 data-subject rights", () => {
  test("a borrower sees and exports their data and requests deletion; a supervisor sees the request", async ({
    page,
    browser,
  }) => {
    const name = applicantName("Rights Person");
    await submitSmallLoan(page, { name });

    await page.getByRole("link", { name: "My data" }).click();
    await expect(page.getByRole("heading", { name: "My data" })).toBeVisible();
    await expect(page.getByTestId("profile")).toContainText(name);
    await expect(page.getByTestId("applications")).toContainText("SUBMITTED");
    await expect(page.getByTestId("purposes")).toContainText("Credit scoring");

    // AC2: a machine-readable file that holds only this borrower's data
    const [download] = await Promise.all([
      page.waitForEvent("download"),
      page.getByRole("button", { name: "Download my data (JSON)" }).click(),
    ]);
    expect(download.suggestedFilename()).toBe("my-lendflow-data.json");
    const exported = JSON.parse(readFileSync((await download.path())!, "utf8"));
    expect(exported.profile.full_name).toBe(name);
    expect(JSON.stringify(exported)).not.toMatch(/password|hash/i);

    // AC3 + AC4: cancelling records nothing; confirming records it and explains what is kept
    await page.getByRole("button", { name: "Request deletion of my data" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByTestId("deletion-request")).toHaveCount(0);

    await page.getByRole("button", { name: "Request deletion of my data" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Yes, request deletion" }).click();
    await expect(page.getByTestId("deletion-request")).toContainText("We will answer by");
    await expect(page.getByTestId("retained")).toContainText("still being processed");
    await expect(page.getByTestId("retained")).toContainText("Audit log");
    await expect(page.getByRole("button", { name: "Request deletion of my data" })).toHaveCount(0);

    // nothing was deleted
    await page.reload();
    await expect(page.getByTestId("profile")).toContainText(name);

    const supervisor = await staffPage(browser, SUPERVISOR, STAFF_PASSWORD);
    await supervisor.getByRole("link", { name: "Data requests" }).click();
    await expect(supervisor.getByRole("heading", { name: "Data deletion requests" })).toBeVisible();
    await expect(supervisor.getByTestId("data-requests").getByText("Open").first()).toBeVisible();
  });

  test("staff cannot open the borrower's My data page, and an officer cannot open the requests list", async ({
    browser,
  }) => {
    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);

    await expect(officer.getByRole("link", { name: "My data" })).toHaveCount(0);
    await expect(officer.getByRole("link", { name: "Data requests" })).toHaveCount(0);
    await officer.goto("/my-data");
    await expect(officer.getByText("You do not have access to this page.")).toBeVisible();
    await officer.goto("/admin/data-requests");
    await expect(officer.getByText("You do not have access to this page.")).toBeVisible();
  });
});
