import { expect, test } from "@playwright/test";
import { appAlert, fillApplication, fillLoanStep, registerBorrower } from "./helpers";

test.describe("LF-003 loan calculator (public)", () => {
  test("shows the worked example without logging in", async ({ page }) => {
    await page.goto("/calculator");

    await expect(page.getByTestId("monthly")).toHaveText("4,896,311 VND");
    await expect(page.getByTestId("total")).toHaveText("117,511,465 VND");
    await expect(page.getByTestId("interest")).toHaveText("17,511,465 VND");
    await expect(page.getByText(/reducing balance method at 16% a year/)).toBeVisible();
  });

  test("offers only the allowed terms", async ({ page }) => {
    await page.goto("/calculator");
    await expect(page.getByTestId("monthly")).toBeVisible();

    const options = await page.getByLabel("Term").locator("option").allTextContents();
    expect(options).toEqual(["6 months", "12 months", "24 months", "36 months", "60 months"]);
  });

  test("a non-numeric amount gets a message under the field", async ({ page }) => {
    await page.goto("/calculator");
    await expect(page.getByTestId("monthly")).toBeVisible();

    await page.getByLabel("Loan amount (VND)").fill("lots");

    await expect(appAlert(page)).toContainText("Enter the amount as a number");
    await expect(page.getByTestId("monthly")).toHaveCount(0);
  });
});

test.describe("LF-004 application with consent", () => {
  test("a borrower applies and sees the submitted application", async ({ page }) => {
    await registerBorrower(page);
    await page.getByRole("link", { name: "Apply", exact: true }).click();

    await fillApplication(page, { amount: "150000000", term: "24", purpose: "Expand my shop" });
    await expect(page.getByText("Credit scoring")).toBeVisible();
    await expect(page.getByText(/Retention period/)).toBeVisible();
    await page.getByRole("checkbox").check();
    await page.getByRole("button", { name: "Submit application" }).click();

    await expect(page).toHaveURL(/\/applications\/[0-9a-f-]{36}$/);
    await expect(page.getByRole("heading", { name: "Application summary" })).toBeVisible();
    await expect(page.getByTestId("status")).toHaveText(/SUBMITTED/i);
    // The hidden /apply page stays in the DOM, so look inside the summary only.
    const summary = page.getByRole("region", { name: "Application summary" });
    await expect(summary.getByText("150,000,000 VND")).toBeVisible();
    await expect(summary.getByText("24 months")).toBeVisible();
  });

  test("unticked consent blocks submission and highlights the checkbox", async ({ page }) => {
    await registerBorrower(page);
    await page.getByRole("link", { name: "Apply", exact: true }).click();
    await fillApplication(page, { amount: "50000000" });

    await page.getByRole("button", { name: "Submit application" }).click();

    await expect(page.getByText(/must accept the consent statement/)).toBeVisible();
    await expect(page.getByRole("checkbox")).toBeFocused();
    await expect(page).toHaveURL(/\/apply$/);
  });

  test("an amount outside the range is refused and nothing is saved", async ({ page }) => {
    await registerBorrower(page);
    await page.getByRole("link", { name: "Apply", exact: true }).click();
    let posted = false;
    page.on("request", (r) => {
      if (r.method() === "POST" && r.url().endsWith("/api/applications")) posted = true;
    });
    await fillLoanStep(page, { amount: "600000000" });

    await page.getByRole("button", { name: "Next", exact: true }).click();

    await expect(page.getByText(/must be between 1,000,000 VND and 500,000,000 VND/)).toBeVisible();
    expect(posted).toBe(false);
  });

  test("a loan under the threshold may leave the purpose blank", async ({ page }) => {
    await registerBorrower(page);
    await page.getByRole("link", { name: "Apply", exact: true }).click();
    await fillApplication(page, { amount: "50000000" });
    await page.getByRole("checkbox").check();

    await page.getByRole("button", { name: "Submit application" }).click();

    await expect(page).toHaveURL(/\/applications\/[0-9a-f-]{36}$/);
  });

  test("the calculator link carries amount and term into the form", async ({ page }) => {
    await page.goto("/calculator");
    await expect(page.getByTestId("monthly")).toBeVisible();
    await registerBorrower(page);

    await page.goto("/apply?amount=75000000&term=36");

    await expect(page.getByLabel(/Loan amount/)).toHaveValue("75,000,000");
    await expect(page.getByLabel("Term")).toHaveValue("36");
  });

  test("the server's age rule is shown and the data is kept", async ({ page }) => {
    await registerBorrower(page);
    await page.getByRole("link", { name: "Apply", exact: true }).click();
    await fillApplication(page, { amount: "50000000", dateOfBirth: "2015-01-01" });
    await page.getByRole("checkbox").check();

    await page.getByRole("button", { name: "Submit application" }).click();

    await expect(appAlert(page)).toContainText(/at least 18/);
    await page.getByRole("button", { name: "Back" }).click();
    await expect(page.getByLabel("Full name")).toHaveValue("Nguyen Test");
  });
});
