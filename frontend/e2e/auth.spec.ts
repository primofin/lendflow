import { expect, test } from "@playwright/test";

import {
  appAlert,
  BORROWER_PASSWORD,
  expectLoggedInAs,
  logIn,
  logOut,
  signIn,
  OFFICER,
  STAFF_PASSWORD,
  SUPERVISOR,
  uniqueEmail,
} from "./helpers";

async function register(
  page: import("@playwright/test").Page,
  email: string,
  password: string,
) {
  await page.goto("/register");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
}

test.describe("LF-001 register and log in", () => {
  test("a new borrower registers, is logged in, logs out and logs in again", async ({
    page,
  }) => {
    const email = uniqueEmail("borrower");

    await register(page, email, BORROWER_PASSWORD);
    await expect(page).toHaveURL("/");
    await expectLoggedInAs(page, email, "borrower");
    await expect(
      page.getByText("You have no applications yet."),
    ).toBeVisible();

    await logOut(page);
    await expect(page.getByRole("link", { name: "Log in" })).toBeVisible();

    await logIn(page, email, BORROWER_PASSWORD);
    await expectLoggedInAs(page, email, "borrower");
  });

  test("the session survives a page reload (refresh cookie)", async ({
    page,
  }) => {
    const email = uniqueEmail("reload");
    await register(page, email, BORROWER_PASSWORD);
    await expectLoggedInAs(page, email, "borrower");

    await page.reload();

    await expectLoggedInAs(page, email, "borrower");
  });

  test("the refresh token is not readable by page scripts", async ({
    page,
    context,
  }) => {
    await register(page, uniqueEmail("cookie"), BORROWER_PASSWORD);
    await expect(page.getByRole("button", { name: "Log out" })).toBeVisible();

    const cookie = (await context.cookies()).find(
      (c) => c.name === "lf_refresh",
    );
    expect(cookie?.httpOnly).toBe(true);
    expect(cookie?.sameSite).toBe("Strict");
    expect(await page.evaluate(() => document.cookie)).not.toContain(
      "lf_refresh",
    );
    expect(
      await page.evaluate(() =>
        JSON.stringify({ ...localStorage, ...sessionStorage }),
      ),
    ).toBe("{}");
  });

  test("registering an existing email shows the message", async ({ page }) => {
    const email = uniqueEmail("dup");
    await register(page, email, BORROWER_PASSWORD);
    await logOut(page);

    await register(page, email, BORROWER_PASSWORD);

    await expect(appAlert(page)).toHaveText("This email is already registered");
    await expect(page).toHaveURL(/\/register$/);
  });

  test("a password shorter than 10 characters is refused with the policy message", async ({
    page,
  }) => {
    await register(page, uniqueEmail("short"), "short");

    await expect(appAlert(page)).toContainText("at least 10 characters");
    await expect(page).toHaveURL(/\/register$/);
  });

  test("wrong credentials show the message, and five in a row lock the account", async ({
    page,
  }) => {
    const email = uniqueEmail("lock");
    await register(page, email, BORROWER_PASSWORD);
    await logOut(page);

    await logIn(page, email, "wrong-password-1");
    await expect(appAlert(page)).toHaveText("Incorrect email or password");
    for (let attempt = 2; attempt <= 5; attempt += 1) {
      await page.getByLabel("Password").fill("wrong-password-1");
      await page.getByRole("button", { name: "Log in" }).click();
      await expect(appAlert(page)).toBeVisible();
    }

    // Even the correct password is refused while the account is locked.
    await page.getByLabel("Password").fill(BORROWER_PASSWORD);
    await page.getByRole("button", { name: "Log in" }).click();
    await expect(appAlert(page)).toContainText("locked for 15 minutes");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("an expired session sends the user to log in with an explanation", async ({
    page,
    context,
  }) => {
    await signIn(page, SUPERVISOR, STAFF_PASSWORD);
    await expectLoggedInAs(page, SUPERVISOR, "supervisor");

    // Simulate the idle timeout: the server no longer renews the session.
    await context.clearCookies();
    await page.route("**/api/users", (route) =>
      route.fulfill({
        status: 401,
        json: { detail: "Not authenticated. Log in again." },
      }),
    );
    await page.getByRole("link", { name: "Users" }).click();

    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("status")).toContainText(
      "signed out after being idle",
    );
  });
});

test.describe("LF-002 roles", () => {
  test("an anonymous visitor to the admin page is sent to log in", async ({
    page,
  }) => {
    await page.goto("/admin/users");

    await expect(page).toHaveURL(/\/login$/);
  });

  test("a supervisor creates an officer, who logs in and cannot see or open user management", async ({
    page,
  }) => {
    const email = uniqueEmail("new-officer");

    await signIn(page, SUPERVISOR, STAFF_PASSWORD);
    await page.getByRole("link", { name: "Users" }).click();
    await expect(
      page.getByRole("heading", { name: "Users", level: 1 }),
    ).toBeVisible();
    await page.getByRole("textbox", { name: "Email" }).fill(email);
    await page.locator("#new-password").fill("officer-password-1");
    await page
      .getByRole("combobox", { name: "Role", exact: true })
      .selectOption("officer");
    await page.getByRole("button", { name: "Create user" }).click();
    await expect(page.getByRole("status")).toHaveText(
      `Created ${email} as officer.`,
    );
    await expect(page.getByRole("cell", { name: email })).toBeVisible();
    await logOut(page);

    await logIn(page, email, "officer-password-1");
    await expect(page).toHaveURL("/");
    await expectLoggedInAs(page, email, "officer");
    await expect(page.getByRole("link", { name: "Users" })).toHaveCount(0);

    await page.goto("/admin/users");
    await expect(appAlert(page)).toHaveText(
      "You do not have access to this page.",
    );
    await expect(
      page.getByRole("heading", { name: "Create a user" }),
    ).toHaveCount(0);
  });

  test("a supervisor cannot change their own role", async ({ page }) => {
    await signIn(page, SUPERVISOR, STAFF_PASSWORD);
    await page.getByRole("link", { name: "Users" }).click();

    await page.getByLabel(`Role for ${SUPERVISOR}`).selectOption("officer");

    await expect(appAlert(page)).toBeVisible();
    await expect(page.getByLabel(`Role for ${SUPERVISOR}`)).toHaveValue(
      "supervisor",
    );
  });

  test("seeded staff can log in", async ({ page }) => {
    await logIn(page, OFFICER, STAFF_PASSWORD);
    await expectLoggedInAs(page, OFFICER, "officer");
  });
});
