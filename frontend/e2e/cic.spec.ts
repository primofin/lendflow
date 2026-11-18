import { expect, test } from "@playwright/test";

import {
  applicantName,
  OFFICER,
  openFromQueue,
  staffPage,
  STAFF_PASSWORD,
  submitSmallLoan,
  uploadAll,
} from "./helpers";

// LF-008. The mock bureau's outcome comes from the application id, so about one file in four
// times out on the first try. The webServer sets short timings (3 s run, 4 s timeout), so both
// paths finish in seconds and this test accepts either.
test.describe("LF-008 mock credit check", () => {
  test("an officer runs the check, sees progress, and gets a debt group", async ({ page, browser }) => {
    const name = applicantName("Cic Check");
    await submitSmallLoan(page, { name });
    await uploadAll(page, 1);
    await expect(page.getByTestId("status")).toHaveText("IN_REVIEW");

    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);
    await openFromQueue(officer, name);

    await officer.getByRole("button", { name: "Run credit check" }).click();
    await expect(officer.getByRole("progressbar", { name: "Credit check progress" })).toBeVisible();
    await expect(officer.getByTestId("cic-remaining")).toBeVisible();
    await expect(officer.getByRole("button", { name: "Run credit check" })).toHaveCount(0);

    await expect(officer.getByTestId("cic-result")).toBeVisible({ timeout: 30_000 });
    await expect(officer.getByTestId("cic-group")).toHaveText(/^[1-5]$/);
    await expect(officer.getByRole("progressbar")).toHaveCount(0);

    // The result is only advice: the file is still waiting for a human decision (BR-15).
    await expect(officer.getByTestId("status")).toHaveText("IN_REVIEW");

    // Progress and result are kept on the server, so a reload shows the same result.
    const group = await officer.getByTestId("cic-group").innerText();
    await officer.reload();
    await expect(officer.getByTestId("cic-group")).toHaveText(group);
  });
});
