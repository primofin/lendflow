import { expect, test } from "@playwright/test";

import {
  appAlert,
  jpeg,
  missingItems,
  OFFICER,
  STAFF_PASSWORD,
  submitSmallLoan,
  uploadFirstMissing,
} from "./helpers";

const BACKEND = "http://localhost:8100";

test.describe("LF-005 / LF-007 / LF-012 borrower application page", () => {
  test("shows progress, the synthetic notice and what is still needed", async ({ page }) => {
    await submitSmallLoan(page);

    const steps = page.getByRole("listitem").filter({ hasText: /Received|Under assessment/ });
    await expect(page.getByText("Received").first()).toBeVisible();
    await expect(page.locator('[aria-current="step"]')).toContainText("Received");
    await expect(page.getByText(/synthetic|non-real/i).first()).toBeVisible();
    await expect(page.getByTestId("checklist-status")).toContainText("still needed");
    expect(await steps.count()).toBeGreaterThan(0);
  });

  test("uploading every required document completes the checklist and queues the file", async ({
    page,
  }) => {
    await submitSmallLoan(page);
    await expect(missingItems(page).first()).toBeVisible(); // the checklist loads after the page
    const needed = await missingItems(page).count();
    expect(needed).toBeGreaterThan(0);

    for (let i = 0; i < needed; i += 1) {
      await uploadFirstMissing(page, i + 1);
      await expect(missingItems(page)).toHaveCount(needed - i - 1);
    }

    await expect(page.getByTestId("checklist-status")).toHaveText("Complete");
    await expect(page.getByTestId("documents").getByRole("listitem")).toHaveCount(needed);
    await expect(page.getByTestId("status")).toHaveText("IN_REVIEW");
    await expect(page.locator('[aria-current="step"]')).toContainText("Under assessment");
  });

  test("a file over 5 MB and a wrong type are refused with a specific message", async ({
    page,
  }) => {
    await submitSmallLoan(page);
    const item = missingItems(page).first();

    await item.locator('input[type="file"]').setInputFiles({
      name: "big.jpg",
      mimeType: "image/jpeg",
      buffer: Buffer.alloc(5 * 1024 * 1024 + 1, 1),
    });
    await item.getByRole("button", { name: /Upload/ }).click();
    await expect(appAlert(page)).toContainText(/over the 5 MB limit/);

    await item.locator('input[type="file"]').setInputFiles({
      name: "notes.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("hello"),
    });
    await item.getByRole("button", { name: /Upload/ }).click();
    await expect(appAlert(page)).toContainText(/not a JPG, PNG or PDF/);
    await expect(page.getByText("No documents uploaded yet.")).toBeVisible();
  });

  test("a file with a PDF name but other content is refused by the server", async ({ page }) => {
    await submitSmallLoan(page);
    const item = missingItems(page).first();

    await item.locator('input[type="file"]').setInputFiles({
      name: "fake.pdf",
      mimeType: "application/pdf",
      buffer: Buffer.from("this is plain text, not a pdf"),
    });
    await item.getByRole("button", { name: /Upload/ }).click();

    await expect(appAlert(page)).toContainText(/Unsupported file type/);
    await expect(page.getByText("No documents uploaded yet.")).toBeVisible();
  });

  test("sending the same file twice stores it once", async ({ page }) => {
    await submitSmallLoan(page);
    await uploadFirstMissing(page, 9);
    await expect(page.getByTestId("documents").getByRole("listitem")).toHaveCount(1);

    // "Add another document" accepts any type; the same bytes are the same file.
    const extra = page.getByRole("heading", { name: "Add another document" }).locator("..");
    await extra.locator('input[type="file"]').setInputFiles(jpeg(9));
    await extra.getByRole("button", { name: /Upload/ }).click();

    await expect(extra.getByRole("status")).toContainText(/already uploaded/);
    await expect(page.getByTestId("documents").getByRole("listitem")).toHaveCount(1);
  });

  test("the borrower finds the application again from the home page", async ({ page }) => {
    const id = await submitSmallLoan(page);

    await page.getByRole("link", { name: "LendFlow" }).click();

    await expect(page.getByRole("heading", { name: "Your applications" })).toBeVisible();
    await page.getByRole("link", { name: /50,000,000 VND over 12 months/ }).click();
    await expect(page).toHaveURL(new RegExp(`/applications/${id}$`));
  });

  test("when an officer asks for information the borrower sees it and resubmits", async ({
    page,
    playwright,
  }) => {
    const id = await submitSmallLoan(page);
    await expect(missingItems(page).first()).toBeVisible(); // the checklist loads after the page
    const needed = await missingItems(page).count();
    for (let i = 0; i < needed; i += 1) {
      await uploadFirstMissing(page, 20 + i);
      await expect(missingItems(page)).toHaveCount(needed - i - 1);
    }
    await expect(page.getByTestId("status")).toHaveText("IN_REVIEW");

    const api = await playwright.request.newContext({ baseURL: BACKEND });
    const login = await api.post("/auth/login", {
      data: { email: OFFICER, password: STAFF_PASSWORD },
    });
    const headers = { Authorization: `Bearer ${(await login.json()).access_token}` };
    expect((await api.post(`/applications/${id}/claim`, { headers })).ok()).toBe(true);
    const asked = await api.post(`/applications/${id}/decision`, {
      headers,
      data: {
        outcome: "request_info",
        explanation: "Please confirm your current employer in writing.",
      },
    });
    expect(asked.ok()).toBe(true);

    await page.reload();
    await expect(page.getByRole("heading", { name: "We need more from you" })).toBeVisible();
    await expect(page.getByText("Please confirm your current employer in writing.")).toBeVisible();
    await expect(page.getByTestId("status")).toHaveText("NEEDS_INFO");

    await page.getByRole("button", { name: "Resubmit for review" }).click();

    await expect(page.getByRole("heading", { name: "We need more from you" })).toHaveCount(0);
    await expect(page.getByTestId("status")).toHaveText("IN_REVIEW");
  });
});
