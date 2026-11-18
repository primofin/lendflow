import { readFileSync } from "node:fs";

import { expect, test } from "@playwright/test";

import { OFFICER, registerBorrower, staffPage, STAFF_PASSWORD, uniqueEmail } from "./helpers";

const HEADER =
  "email,full_name,date_of_birth,national_id,address,income_type,monthly_income_vnd,existing_debt_payment_vnd,amount_vnd,term_months,purpose";

function row(email: string, over: { national_id?: string } = {}) {
  return `${email},Import Person,1990-05-01,${over.national_id ?? "012345678901"},1 Example Street Hanoi,salaried,30000000,0,50000000,12,`;
}

function file(lines: string[]) {
  return { name: "people.csv", mimeType: "text/csv", buffer: Buffer.from([HEADER, ...lines].join("\n") + "\n") };
}

test.describe("LF-013 CSV bulk import", () => {
  test("an officer imports a file, sees the counts and the error report, and a repeat is skipped", async ({
    browser,
  }) => {
    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);
    const good = uniqueEmail("import-a");
    const bad = uniqueEmail("import-b");
    const upload = file([row(good), row(bad, { national_id: "123" })]);

    await officer.getByRole("link", { name: "Import", exact: true }).click();
    await expect(officer.getByRole("heading", { name: "Import applications from CSV" })).toBeVisible();

    await officer.getByLabel("CSV file", { exact: true }).setInputFiles(upload);
    await officer.getByRole("button", { name: "Import", exact: true }).click();

    await expect(officer.getByTestId("count-total")).toHaveText("2");
    await expect(officer.getByTestId("count-imported")).toHaveText("1");
    await expect(officer.getByTestId("count-invalid")).toHaveText("1");
    await expect(officer.getByTestId("issues")).toContainText("National ID must be 12 digits");
    await expect(officer.getByTestId("issues")).not.toContainText("123,");

    const [download] = await Promise.all([
      officer.waitForEvent("download"),
      officer.getByRole("button", { name: "Download the error report" }).click(),
    ]);
    expect(download.suggestedFilename()).toBe("import-report.csv");
    const report = readFileSync((await download.path())!, "utf8");
    expect(report).toContain("row,type,reason");
    expect(report).toContain("3,invalid,national_id: National ID must be 12 digits");

    // the imported draft opens in the staff file view and is still only a draft
    await officer.getByRole("link", { name: "open the draft" }).click();
    await expect(officer.getByTestId("status")).toHaveText("DRAFT");

    // the same file again: the good row is now a duplicate
    await officer.goto("/import");
    await officer.getByLabel("CSV file", { exact: true }).setInputFiles(upload);
    await officer.getByRole("button", { name: "Import", exact: true }).click();
    await expect(officer.getByTestId("count-imported")).toHaveText("0");
    await expect(officer.getByTestId("count-duplicates")).toHaveText("1");
    await expect(officer.getByTestId("issues")).toContainText("already exists or was already imported");
  });

  test("a file with the wrong columns is refused with a specific message", async ({ browser }) => {
    const officer = await staffPage(browser, OFFICER, STAFF_PASSWORD);
    await officer.goto("/import");

    await officer.getByLabel("CSV file", { exact: true }).setInputFiles({
      name: "wrong.csv",
      mimeType: "text/csv",
      buffer: Buffer.from("email,shoe_size\na@example.com,42\n"),
    });
    await officer.getByRole("button", { name: "Import", exact: true }).click();

    await expect(officer.getByRole("alert").filter({ hasText: "Missing columns" })).toContainText(
      "Unexpected columns: shoe_size",
    );
    await expect(officer.getByTestId("import-result")).toHaveCount(0);
  });

  test("a borrower has no Import link and cannot open the page", async ({ page }) => {
    await registerBorrower(page);

    await expect(page.getByRole("link", { name: "Import", exact: true })).toHaveCount(0);
    await page.goto("/import");
    await expect(page.getByText("You do not have access to this page.")).toBeVisible();
  });
});
