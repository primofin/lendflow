import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

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

const LONG_REASON = "Your monthly income does not cover the repayments for this loan.";

/** A borrower's fully documented, queued application. Returns its id. */
async function queuedApplication(
  page: Page,
  name: string,
  opts: { amount?: string; purpose?: string } = {},
): Promise<string> {
  const id = await submitSmallLoan(page, { name, ...opts });
  await uploadAll(page, 1);
  await expect(page.getByTestId("status")).toHaveText("IN_REVIEW");
  return id;
}

async function decide(page: Page, outcome: string) {
  await page.getByLabel("Your decision").selectOption(outcome);
}

async function confirmDecision(page: Page) {
  await page.getByRole("button", { name: /^Review (decision|correction)$/ }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Confirm and record" }).click();
}

test.describe("LF-011 decisions", () => {
  test("a rejection needs reasons; once recorded the borrower sees them and what could change", async ({
    page,
    browser,
  }) => {
    const name = applicantName("Decide Reject");
    await queuedApplication(page, name);
    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);
    await openFromQueue(officer, name);

    await decide(officer, "reject");
    await officer.getByRole("button", { name: "Review decision" }).click();
    await expect(officer.getByText(/Choose a reason code/)).toBeVisible();
    await expect(officer.getByRole("dialog")).toHaveCount(0);

    await officer.getByLabel("Reason code").selectOption({ index: 1 });
    const reason = await officer.getByLabel("Reason code").locator("option:checked").innerText();
    await officer.getByLabel("Explanation for the borrower").fill(LONG_REASON);
    await officer.getByLabel(/could change the outcome/).fill("A co-borrower with income.");
    await confirmDecision(officer);

    await expect(officer.getByTestId("status")).toHaveText("REJECTED");
    const history = officer.getByTestId("decision-history").getByRole("listitem");
    await expect(history).toHaveCount(1);
    await expect(history.first()).toContainText("Rejected");
    await expect(history.first()).toContainText("You");

    await page.reload();
    const box = page.getByTestId("decision");
    await expect(box).toContainText("Not approved");
    await expect(box).toContainText(reason);
    await expect(box).toContainText(LONG_REASON);
    await expect(box).toContainText("A co-borrower with income.");
    await expect(page.getByTestId("status")).toHaveText("REJECTED");
  });

  test("a request for information reaches the borrower, who answers and returns the file", async ({
    page,
    browser,
  }) => {
    const name = applicantName("Decide Info");
    await queuedApplication(page, name);
    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);
    await openFromQueue(officer, name);

    await decide(officer, "request_info");
    await officer.getByLabel("What the borrower must add").fill("Please send a signed employer letter.");
    await confirmDecision(officer);
    await expect(officer.getByTestId("status")).toHaveText("NEEDS_INFO");

    await page.reload();
    await expect(page.getByText("Please send a signed employer letter.")).toBeVisible();
    await page.getByRole("button", { name: "Resubmit for review" }).click();
    await expect(page.getByTestId("status")).toHaveText("IN_REVIEW");

    await officer.reload();
    await expect(officer.getByTestId("status")).toHaveText("IN_REVIEW");
    await expect(officer.getByTestId("decision-history").getByRole("listitem")).toHaveCount(1);
  });

  test("an officer cannot approve a large loan; referring it lets a supervisor approve", async ({
    page,
    browser,
  }) => {
    const name = applicantName("Decide Large");
    const id = await queuedApplication(page, name, {
      amount: "250000000",
      purpose: "Open a second shop",
    });
    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);
    await openFromQueue(officer, name);

    await decide(officer, "approve");
    await confirmDecision(officer);

    await expect(officer.getByText("Supervisor approval required")).toBeVisible();
    await expect(officer.getByTestId("status")).toHaveText("IN_REVIEW");

    await decide(officer, "refer");
    await confirmDecision(officer);
    await expect(officer.getByTestId("status")).toHaveText("REFERRED");
    await expect(officer.getByText(/Only a supervisor can decide it/)).toBeVisible();
    await expect(officer.getByLabel("Your decision")).toHaveCount(0);

    const supervisor = await staffPage(browser, SUPERVISOR, STAFF_PASSWORD);
    await supervisor.goto(`/review/${id}`);
    await expect(supervisor.getByTestId("status")).toHaveText("REFERRED");
    await expect(supervisor.getByRole("option", { name: "Refer to a supervisor" })).toHaveCount(0);
    await decide(supervisor, "approve");
    await confirmDecision(supervisor);

    await expect(supervisor.getByTestId("status")).toHaveText("APPROVED");
    await page.reload();
    await expect(page.getByTestId("status")).toHaveText("APPROVED");
  });

  test("only a supervisor can correct a rejection, and both entries stay visible", async ({
    page,
    browser,
  }) => {
    const name = applicantName("Decide Correct");
    const id = await queuedApplication(page, name);
    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);
    await openFromQueue(officer, name);
    await decide(officer, "reject");
    await officer.getByLabel("Reason code").selectOption({ index: 1 });
    await officer.getByLabel("Explanation for the borrower").fill(LONG_REASON);
    await officer.getByLabel(/could change the outcome/).fill("Proof of additional income.");
    await confirmDecision(officer);
    await expect(officer.getByTestId("status")).toHaveText("REJECTED");
    await expect(officer.getByRole("button", { name: "Correct this decision" })).toHaveCount(0);

    const supervisor = await staffPage(browser, SUPERVISOR, STAFF_PASSWORD);
    await supervisor.goto(`/review/${id}`);
    await supervisor.getByRole("button", { name: "Correct this decision" }).click();
    await decide(supervisor, "approve");
    await confirmDecision(supervisor);

    await expect(supervisor.getByTestId("status")).toHaveText("APPROVED");
    const history = supervisor.getByTestId("decision-history").getByRole("listitem");
    await expect(history).toHaveCount(2);
    await expect(history.nth(0)).toContainText("Rejected");
    await expect(history.nth(0)).toContainText("Corrected by a later decision");
    await expect(history.nth(1)).toContainText("Approved");
    await expect(history.nth(1)).toContainText("Corrects an earlier decision");
    await expect(supervisor.getByRole("button", { name: "Correct this decision" })).toBeVisible();

    await page.reload();
    await expect(page.getByTestId("status")).toHaveText("APPROVED");
  });

  test("cancelling the confirmation records nothing", async ({ page, browser }) => {
    const name = applicantName("Decide Cancel");
    await queuedApplication(page, name);
    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);
    await openFromQueue(officer, name);

    await decide(officer, "approve");
    await officer.getByRole("button", { name: "Review decision" }).click();
    await expect(officer.getByRole("dialog")).toContainText("cannot be deleted");
    await officer.getByRole("dialog").getByRole("button", { name: "Cancel" }).click();

    await expect(officer.getByRole("dialog")).toHaveCount(0);
    await expect(officer.getByTestId("status")).toHaveText("IN_REVIEW");
    await expect(officer.getByText("No decision has been recorded yet.")).toBeVisible();
  });
});
