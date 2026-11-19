import { expect, test, type Page } from "@playwright/test";

import {
  applicantName,
  OFFICER,
  openFromQueue,
  staffPage,
  STAFF_PASSWORD,
  submitSmallLoan,
  uploadAll,
} from "./helpers";

async function approvedFile(page: Page, browser: Parameters<typeof staffPage>[0], amount: string) {
  const name = applicantName("Disburse Person");
  await submitSmallLoan(page, { name, amount });
  await uploadAll(page, 1);
  const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);
  await openFromQueue(officer, name);
  await officer.getByLabel("Your decision").selectOption("approve");
  await officer.getByRole("button", { name: /^Review (decision|correction)$/ }).click();
  await officer.getByRole("dialog").getByRole("button", { name: "Confirm and record" }).click();
  await expect(officer.getByTestId("status")).toHaveText("APPROVED");
  return officer;
}

test.describe("LF-020 biometric step before a large disbursement", () => {
  test("above 10M VND a failed face match blocks the payout; a passed one allows it", async ({
    page,
    browser,
  }) => {
    const officer = await approvedFile(page, browser, "50000000");
    const disburse = officer.getByRole("button", { name: /^Disburse/ });
    await expect(disburse).toBeDisabled();

    await officer.getByRole("button", { name: "Simulate face match: fail" }).click();
    await expect(officer.getByTestId("face-match-result")).toContainText("failed");
    await expect(disburse).toBeDisabled();

    await officer.getByRole("button", { name: "Simulate face match: pass" }).click();
    await expect(officer.getByTestId("face-match-result")).toContainText("passed");
    await disburse.click();
    await expect(officer.getByTestId("disbursed")).toContainText("Disbursed 50,000,000 VND");
  });

  test("at or below 10M VND there is no face-match step", async ({ page, browser }) => {
    const officer = await approvedFile(page, browser, "5000000");

    await expect(officer.getByRole("button", { name: "Simulate face match: pass" })).toHaveCount(0);
    await officer.getByRole("button", { name: "Disburse 5,000,000 VND" }).click();
    await expect(officer.getByTestId("disbursed")).toContainText("Disbursed 5,000,000 VND");
  });
});
