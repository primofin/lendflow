import { expect, test } from "@playwright/test";

test.describe("dark mode", () => {
  test.use({ colorScheme: "light" });

  test("the toggle switches theme and the choice survives a reload", async ({ page }) => {
    await page.goto("/");
    const html = page.locator("html");
    await expect(html).toHaveAttribute("data-theme", "light");

    await page.getByRole("button", { name: "Switch to dark theme" }).click();
    await expect(html).toHaveAttribute("data-theme", "dark");

    await page.reload();
    await expect(html).toHaveAttribute("data-theme", "dark");
    await page.getByRole("button", { name: "Switch to light theme" }).click();
    await expect(html).toHaveAttribute("data-theme", "light");
  });

  test("with no saved choice the system setting decides", async ({ browser }) => {
    const context = await browser.newContext({ colorScheme: "dark" });
    const page = await context.newPage();
    await page.goto("/");

    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await context.close();
  });
});
